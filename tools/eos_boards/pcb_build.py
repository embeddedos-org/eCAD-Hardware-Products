"""Build a board in KiCad from a design spec; run with KiCad's own Python.

    python3 pcb_build.py place  spec.json board.kicad_pcb board.dsn
    python3 pcb_build.py finish spec.json board.kicad_pcb board.ses

``place`` loads every footprint from KiCad's libraries, puts it where the design says, gives
each pad its net, links it to its schematic symbol (so ``kicad-cli pcb drc
--schematic-parity`` can prove the board matches the schematic), draws the outline, the
design rules, net classes and ground pours, and writes a Specctra DSN for the autorouter.
``finish`` imports the routed session, refills the pours and saves.
"""

import json
import sys
from pathlib import Path

import pcbnew as P

import fabrication   # this folder's own module (the script's directory is on sys.path)

def MM(mm):
    """Millimetres to KiCad's internal nanometres, rounded. pcbnew.FromMM truncates, so 26.3 + 6.0
    (32.29999... in floating point) would land 1 nm short of 32.3 mm."""
    return int(round(mm * 1_000_000))


def v(x, y):
    return P.VECTOR2I(MM(x), MM(y))


# Items taken off the board, kept referenced until the process exits. KiCad 10's SWIG proxies for
# removed tracks and vias break the bindings when they are garbage-collected: the next
# board.GetTracks() raises "TypeError: 'swig_runtime_data5.SwigPyObject' object is not iterable"
# and the process ends with exit 139 (EoS Feather RP2040, 3 builds of 4). Holding them here avoids
# it; the board's geometry is unchanged. Every removal goes through _remove (issue #70).
_REMOVED = []


def _remove(board, item):
    """Take ``item`` off ``board`` and keep it referenced in _REMOVED, so Python never frees its
    proxy while the board is in use. The item can still be added back (repair's all-or-nothing undo)."""
    board.Remove(item)
    _REMOVED.append(item)


def outline(board, w, h, r):
    def seg(a, b):
        s = P.PCB_SHAPE(board)
        s.SetShape(P.SHAPE_T_SEGMENT)
        s.SetStart(v(*a))
        s.SetEnd(v(*b))
        s.SetLayer(P.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(c, start):
        s = P.PCB_SHAPE(board)
        s.SetShape(P.SHAPE_T_ARC)
        s.SetCenter(v(*c))
        s.SetStart(v(*start))
        s.SetArcAngleAndEnd(P.EDA_ANGLE(90, P.DEGREES_T), True)
        s.SetLayer(P.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    seg((r, 0), (w - r, 0))
    seg((w, r), (w, h - r))
    seg((w - r, h), (r, h))
    seg((0, h - r), (0, r))
    arc((w - r, r), (w - r, 0))
    arc((w - r, h - r), (w, h - r))
    arc((r, h - r), (r, h))
    arc((r, r), (0, r))


def rules(board, spec):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(spec.get("layers", 2))
    ds.SetBoardThickness(MM(spec["thickness"]))
    r = spec["rules"]
    ds.m_TrackMinWidth = MM(r["min_track"])
    ds.m_MinClearance = MM(r["min_clearance"])
    ds.m_ViasMinSize = MM(r["min_via"])
    ds.m_MinThroughDrill = MM(r["min_drill"])
    ds.m_CopperEdgeClearance = MM(r["edge_clearance"])
    ds.m_HoleClearance = MM(r["hole_clearance"])
    ns = ds.m_NetSettings
    default = ns.GetDefaultNetclass()
    default.SetTrackWidth(MM(r["track"]))
    default.SetClearance(MM(r["clearance"]))
    default.SetViaDiameter(MM(r["via"]))
    default.SetViaDrill(MM(r["drill"]))
    for name, c in spec["netclasses"].items():
        nc = P.NETCLASS(name)
        nc.SetTrackWidth(MM(c["track"]))
        nc.SetClearance(MM(c["clearance"]))
        nc.SetViaDiameter(MM(c.get("via", r["via"])))
        nc.SetViaDrill(MM(c.get("drill", r["drill"])))
        ns.SetNetclass(name, nc)
    for net, cls in spec["net_to_class"].items():
        ns.SetNetclassPatternAssignment(net, cls)


def zone(board, net, layer, w, h):
    z = P.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetPadConnection(P.ZONE_CONNECTION_FULL)
    z.SetMinThickness(MM(0.2))
    z.SetThermalReliefGap(MM(0.3))
    z.SetLocalClearance(MM(0.25))
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0, 0), (w, 0), (w, h), (0, h)):
        o.Append(MM(x), MM(y))
    board.Add(z)


def text(board, s, x, y, size, layer=P.F_SilkS, angle=0.0, bold=False, mirror=False):
    t = P.PCB_TEXT(board)
    t.SetText(s)
    t.SetMirrored(mirror)
    t.SetPosition(v(x, y))
    t.SetLayer(layer)
    t.SetTextSize(v(size, size))
    t.SetTextThickness(MM(fabrication.silk_stroke(size, bold)))     # 15 % of the height (20 % bold), >= 0.15 mm
    t.SetTextAngleDegrees(angle)
    board.Add(t)
    return t


def _box(center, half):
    return P.BOX2I(P.VECTOR2I(center.x - half, center.y - half), P.VECTOR2I(2 * half, 2 * half))


HOLE_TO_HOLE = 0.25   # mm between drilled holes, of any net: KiCad's default and a common fab minimum
# A via keeps this far (mm) from a surface pad of its own net: a solder-mask web between the
# two tents the via, so the pad's solder cannot run into its barrel.
VIA_PAD_GAP = 0.1
ROUTER_MARGIN = 0.01   # mm of clearance the router sees beyond the board's rules (see place)


def track_width(spec, net):
    """The width the board's net classes give ``net`` (nm), as the autorouter uses: a pre-route or
    a repair laid narrower would leave the net below its class, 0.2 mm USB at 0.15 mm, say."""
    cls = spec.get("net_to_class", {}).get(net.GetNetname())
    return MM(spec["netclasses"][cls]["track"] if cls else spec["rules"]["track"])


def _inside(spec, pos, margin):
    """True when ``pos`` (nm) lies inside the board's rounded-rectangle outline by at least
    ``margin`` (nm), corners included, and at least ``margin`` from every copper keep-out (an
    antenna cut-out) and every fiducial's copper-free square: a rectangle test alone lets copper
    into a cut-away corner."""
    w, h, r = MM(spec["width"]), MM(spec["height"]), MM(spec["corner_radius"])
    x, y = pos.x, pos.y
    if not (margin <= x <= w - margin and margin <= y <= h - margin):
        return False
    for x_0, y_0, x_1, y_1 in spec.get("copper_keepouts", []) + [k[:4] for k in spec.get("fiducial_keepouts", [])]:
        if MM(x_0) - margin < x < MM(x_1) + margin and MM(y_0) - margin < y < MM(y_1) + margin:
            return False
    cx = r if x < r else w - r if x > w - r else None
    cy = r if y < r else h - r if y > h - r else None
    if cx is None or cy is None:
        return True
    return (x - cx) ** 2 + (y - cy) ** 2 <= (r - margin) ** 2 if r > margin else False


def _in_fiducial_keepout(spec, pos, margin):
    """True when ``pos`` (nm) lies within ``margin`` of a fiducial's copper-free square (any side: the
    generator keeps its own copper out of both layers there)."""
    return any(MM(k[0]) - margin < pos.x < MM(k[2]) + margin and MM(k[1]) - margin < pos.y < MM(k[3]) + margin
               for k in spec.get("fiducial_keepouts", []))


def _holes(board):
    """(centre, drill radius) of every drilled hole on the board: vias and through-hole pads."""
    out = [(t.GetPosition(), t.GetDrillValue() // 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.HasHole():
                out.append((pad.GetPosition(), max(pad.GetDrillSize().x, pad.GetDrillSize().y) // 2))
    return out


def _hole_free(holes, pos, drill):
    """True when a hole of ``drill`` at ``pos`` keeps HOLE_TO_HOLE from every hole in ``holes``,
    whatever its net: two holes too close break into each other when drilled."""
    for c, rad in holes:
        need = drill // 2 + rad + MM(HOLE_TO_HOLE)
        if (c.x - pos.x) ** 2 + (c.y - pos.y) ** 2 < need * need:
            return False
    return True


def _in_bottom_keepout(spec, pos, margin):
    """True when ``pos`` (nm) lies within ``margin`` of a "B.Cu" router keep-out: an area whose
    bottom pour is kept solid (under a crystal, say)."""
    for k in spec.get("router_keepouts", []):
        if len(k) > 4 and k[4] == "B.Cu" and \
                MM(k[0]) - margin < pos.x < MM(k[2]) + margin and MM(k[1]) - margin < pos.y < MM(k[3]) + margin:
            return True
    return False


def _exposed_pad(fp, pad):
    """A chip's exposed pad: the biggest pad of a part with at least four, over 1.5 mm across (a
    QFN-20's is 1.8 mm). A two-pad part's pad or a lone test pad is not one."""
    size = pad.GetBoundingBox()
    if min(size.GetWidth(), size.GetHeight()) <= MM(1.5):
        return False
    pads = list(fp.Pads())
    return (len({q.GetNumber() for q in pads}) >= 4
            and size.GetArea() >= max(q.GetBoundingBox().GetArea() for q in pads))


def fanout(board, spec, only=None, exclude=(), beyond=0, inward=False):
    """Join plane-net pads to their inner plane before routing, as a designer would.

    Every surface pad on a plane net (a capacitor's ground end, a regulator's 3.3 V pin)
    gets a short track and a via, placed outward from its part, on the first side that is
    clear of every other pad and via. An exposed pad gets a 2 x 2 array of vias in the pad.
    The autorouter is then left with the signals; a pad that finds no clear spot is left to it.
    On a board with no inner plane, an exposed pad on a net poured on both outer layers still
    gets its 2 x 2 vias, into the bottom pour: a QFN's centre pad is its ground, and without
    them it hangs on whatever track the router leaves it.
    A part listed in ``ground_vias`` gets the plane treatment there too: a via beside each of
    its pads on such a net.
    Returns (vias placed, pads left to the router).
    """
    r = spec["rules"]
    plane_nets = {pl["net"] for pl in spec.get("planes", [])}
    ep_nets = set() if plane_nets else {z["net"] for z in spec.get("zones", [])
                                        if {"F.Cu", "B.Cu"} <= set(z["layers"])}
    if not plane_nets and not ep_nets:
        return 0, 0
    via_r = MM(r["via"] / 2)
    keep = via_r + MM(r["clearance"] + 0.02)
    obstacles = []   # (box, netcode)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            obstacles.append((pad.GetBoundingBox(), pad.GetNetCode()))
    # copper already on the board (reference copper, pre-routes): vias, tracks and small zones
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            obstacles.append((_box(t.GetPosition(), t.GetWidth(P.F_Cu) // 2), t.GetNetCode()))
            continue
        a, b = t.GetStart(), t.GetEnd()
        n = max(1, int(((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 / MM(0.1)))
        for k in range(n + 1):
            obstacles.append((_box(P.VECTOR2I(int(a.x + (b.x - a.x) * k / n), int(a.y + (b.y - a.y) * k / n)),
                                   t.GetWidth() // 2), t.GetNetCode()))
    plane_layers = {getattr(P, pl["layer"].replace(".", "_")) for pl in spec.get("planes", [])}
    for z in board.Zones():
        if z.GetLayer() not in plane_layers:
            obstacles.append((z.GetBoundingBox(), z.GetNetCode()))
    edge = MM(r["edge_clearance"] + r["via"] / 2 + 0.1)
    w, h = MM(spec["width"]), MM(spec["height"])
    skip = set(spec.get("no_fanout", []))
    # two layers: the parts named here (decoupling capacitors, say) also get a via beside each
    # pad on a pour that covers both layers, so their ground loop closes through the bottom pour
    dogbone = set(spec.get("ground_vias", []))
    bottom_pours = {z["net"] for z in spec.get("zones", []) if "B.Cu" in z["layers"]}
    # every net's surface pads, the exposed ones aside: a via keeps VIA_PAD_GAP from each
    smd_shapes = {}
    for f in board.GetFootprints():
        for q in f.Pads():
            if q.GetAttribute() == P.PAD_ATTRIB_SMD and not _exposed_pad(f, q):
                smd_shapes.setdefault(q.GetNetCode(), []).append(
                    q.GetEffectiveShape(P.F_Cu if q.IsOnLayer(P.F_Cu) else P.B_Cu))
    placed = left = 0

    holes = _holes(board)

    def add_via(pos, net):
        holes.append((pos, MM(r["drill"]) // 2))
        via = P.PCB_VIA(board)
        via.SetPosition(pos)
        via.SetWidth(MM(r["via"]))
        via.SetDrill(MM(r["drill"]))
        via.SetNet(net)
        via.SetLocked(True)      # fixed for the autorouter: Freerouting may otherwise delete or move it
        board.Add(via)
        obstacles.append((_box(pos, via_r), net.GetNetCode()))
        spec.setdefault("fanout_copper", []).append([pos.x, pos.y])    # prune_dangling may still take it

    for fp in board.GetFootprints():
        if (only is not None and fp.GetReference() not in only) or fp.GetReference() in exclude:
            continue
        centre = fp.GetPosition()
        for pad in fp.Pads():
            net = pad.GetNet()
            if net is None or net.GetNetname() not in plane_nets | ep_nets or pad.GetAttribute() != P.PAD_ATTRIB_SMD:
                continue
            if fp.GetReference() in skip and pad.GetNumber() not in spec.get("fanout_pads", {}).get(fp.GetReference(), []):
                continue
            size = pad.GetBoundingBox()
            exposed = _exposed_pad(fp, pad)
            if not exposed and net.GetNetname() not in plane_nets and fp.GetReference() not in dogbone:
                continue                                                 # two layers: exposed pads only
            if exposed and any(q.GetNumber() == pad.GetNumber() and q.GetAttribute() == P.PAD_ATTRIB_PTH
                               for q in fp.Pads()):
                continue                                                 # its footprint has thermal vias
            if exposed:                                                  # exposed pad: vias in the pad
                c = pad.GetPosition()
                # the four vias sit inside the pad: 0.6 mm off centre, or less on a small pad
                off = min(MM(0.6), min(size.GetWidth(), size.GetHeight()) // 2 - via_r - MM(0.05))
                for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    add_via(P.VECTOR2I(c.x + dx * off, c.y + dy * off), net)
                    placed += 1
                continue
            c = pad.GetPosition()
            # Prefer the direction that points away from the busiest part (the MCU), so a via
            # never lands in the channel its signals escape through.
            away = None
            for ax0, ay0 in spec.get("fanout_avoid", []):
                ax, ay = c.x - MM(ax0), c.y - MM(ay0)
                d2 = ax * ax + ay * ay
                if away is None or d2 < away[2]:
                    away = (ax, ay, d2)
            if away is None:
                ax, ay = c.x - centre.x, c.y - centre.y
            else:
                ax, ay = away[0], away[1]
            norm = max(1.0, (ax * ax + ay * ay) ** 0.5)
            out = (ax / norm, ay / norm)
            if inward:
                # across the row, towards the other row: along the pad's long axis, not along the row
                long_y = size.GetHeight() >= size.GetWidth()
                out = (0.0, -1.0 if c.y > centre.y else 1.0) if long_y else (-1.0 if c.x > centre.x else 1.0, 0.0)
            compass = [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7071, 0.7071), (-0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, -0.7071)]
            dirs = sorted(compass, key=lambda d: -(d[0] * out[0] + d[1] * out[1]))[:5]
            reach = max(size.GetWidth(), size.GetHeight()) / 2 + via_r + MM(0.2) + beyond
            # the stub is no wider than the pad, so it fits between fine-pitch neighbours
            stub = min(MM(0.3), min(size.GetWidth(), size.GetHeight()))
            own = smd_shapes.get(net.GetNetCode(), [])   # its own pad and its net's others
            done = False
            for dx, dy in dirs:
                # staggered when neighbours crowd it; the small first steps let a diagonal clear
                # its pad's corner by VIA_PAD_GAP
                for extra in (0, MM(0.1), MM(0.2), MM(0.3), MM(0.6), MM(0.9), MM(1.2)):
                    pos = P.VECTOR2I(int(c.x + dx * (reach + extra)), int(c.y + dy * (reach + extra)))
                    if not _inside(spec, pos, edge):
                        continue
                    if any(sh.Collide(pos, via_r + MM(VIA_PAD_GAP)) for sh in own):
                        continue                                 # a diagonal step can clip a pad's corner
                    if net.GetNetname() not in bottom_pours and _in_bottom_keepout(spec, pos, keep):
                        continue                                 # only the bottom pour's own vias go there
                    if _in_pour_keepout(spec, pos, keep):
                        continue                                 # no pour there for the via to join
                    vb = _box(pos, keep)
                    if any(ob.Intersects(vb) and code != net.GetNetCode() for ob, code in obstacles):
                        continue
                    # The escape track must clear every other net's pad along its whole length.
                    tkeep = stub // 2 + MM(r["clearance"] + 0.02)
                    steps = max(2, int(((pos.x - c.x) ** 2 + (pos.y - c.y) ** 2) ** 0.5 / MM(0.1)))
                    path = [P.VECTOR2I(int(c.x + (pos.x - c.x) * k / steps), int(c.y + (pos.y - c.y) * k / steps))
                            for k in range(1, steps + 1)]
                    if any(ob.Intersects(_box(q, tkeep)) and code != net.GetNetCode()
                           for q in path for ob, code in obstacles):
                        continue
                    if any(_in_fiducial_keepout(spec, q, tkeep) for q in path):
                        continue
                    if any(ob.Intersects(_box(pos, via_r)) and code == net.GetNetCode() and ob != size
                           for ob, code in obstacles):
                        continue
                    if not _hole_free(holes, pos, MM(r["drill"])):
                        continue
                    t = P.PCB_TRACK(board)
                    t.SetStart(c)
                    t.SetEnd(pos)
                    t.SetWidth(stub)
                    t.SetLayer(P.F_Cu if pad.IsOnLayer(P.F_Cu) else P.B_Cu)
                    t.SetNet(net)
                    t.SetLocked(True)    # with its via: the pad's way into the plane stays as laid
                    board.Add(t)
                    spec.setdefault("fanout_copper", []).append([c.x, c.y, pos.x, pos.y])
                    add_via(pos, net)
                    placed += 1
                    done = True
                    break
                if done:
                    break
            if not done:
                left += 1
    return placed, left


REFERENCE_ZONE = "eos-reference"


def copper_keepout(board, points):
    """A rule area on every copper layer that no track, via, pad or pour may enter: an antenna
    cut-out. It stays on the saved board, so zone fills, DRC and the router's DSN all honour it."""
    area = P.ZONE(board)
    area.SetIsRuleArea(True)
    area.SetLayerSet(P.LSET.AllCuMask(board.GetCopperLayerCount()))
    area.SetZoneName("eos-copper-keepout")
    area.SetDoNotAllowTracks(True)
    area.SetDoNotAllowVias(True)
    area.SetDoNotAllowPads(True)
    area.SetDoNotAllowZoneFills(True)
    area.SetDoNotAllowFootprints(False)
    o = area.Outline()
    o.NewOutline()
    for x, y in points:
        o.Append(x, y)
    board.Add(area)


POUR_KEEPOUT = "eos-pour-keepout"


def pour_keepout(board, layer, points):
    """A rule area on one copper layer that no pour may fill, though tracks, vias and pads may
    enter it: under an RL78's crystal, whose manual forbids a ground pattern beneath the X1/X2
    wiring and the resonator. It stays on the saved board, so the zone fill and DRC honour it."""
    area = P.ZONE(board)
    area.SetIsRuleArea(True)
    area.SetLayer(layer)
    area.SetZoneName(POUR_KEEPOUT)
    area.SetDoNotAllowTracks(False)
    area.SetDoNotAllowVias(False)
    area.SetDoNotAllowPads(False)
    area.SetDoNotAllowZoneFills(True)
    area.SetDoNotAllowFootprints(False)
    o = area.Outline()
    o.NewOutline()
    for x, y in points:
        o.Append(x, y)
    board.Add(area)


def _in_pour_keepout(spec, pos, margin):
    """True when ``pos`` (nm) lies within ``margin`` of a pour keep-out on either layer: a via
    there joins no pour on that layer."""
    return any(MM(k[0]) - margin < pos.x < MM(k[2]) + margin and MM(k[1]) - margin < pos.y < MM(k[3]) + margin
               for k in spec.get("pour_keepouts", []))


def _keepout(board, layer, points):
    area = P.ZONE(board)
    area.SetIsRuleArea(True)
    area.SetLayer(layer)
    area.SetDoNotAllowTracks(True)
    area.SetDoNotAllowVias(True)
    area.SetDoNotAllowPads(False)
    area.SetDoNotAllowZoneFills(False)
    area.SetDoNotAllowFootprints(False)
    o = area.Outline()
    o.NewOutline()
    for x, y in points:
        o.Append(int(x), int(y))
    board.Add(area)


def reference_copper(board, spec, nets):
    """Lay down copper taken verbatim from a reference design (tracks, vias, small zones),
    placed relative to the part it was drawn around; see the reference file's own source line.
    Tracks and vias are locked, so the autorouter treats them as fixed."""
    ref = spec["reference_copper"]
    data = json.loads(Path(ref["file"]).read_text())
    ox, oy = ref["origin"]
    for t in data["tracks"]:
        tr = P.PCB_TRACK(board)
        tr.SetStart(v(ox + t["a"][0], oy + t["a"][1]))
        tr.SetEnd(v(ox + t["b"][0], oy + t["b"][1]))
        tr.SetWidth(MM(t["w"]))
        tr.SetLayer(getattr(P, t["layer"].replace(".", "_")))
        tr.SetNet(nets[t["net"]])
        tr.SetLocked(True)
        board.Add(tr)
    for d in data["vias"]:
        via = P.PCB_VIA(board)
        via.SetPosition(v(ox + d["x"], oy + d["y"]))
        via.SetWidth(MM(d["d"]))
        via.SetDrill(MM(d["drill"]))
        via.SetNet(nets[d["net"]])
        via.SetLocked(True)
        board.Add(via)
    for zd in data["zones"]:
        z = P.ZONE(board)
        z.SetZoneName(REFERENCE_ZONE)
        z.SetLayer(getattr(P, zd["layer"].replace(".", "_")))
        z.SetNet(nets[zd["net"]])
        z.SetAssignedPriority(zd["priority"] + 10)     # above the board's own pours
        if zd.get("clearance") is not None:
            z.SetLocalClearance(MM(zd["clearance"]))
        z.SetMinThickness(MM(zd["min_width"]))
        z.SetPadConnection(getattr(P, "ZONE_CONNECTION_" + zd["connection"].upper()))
        o = z.Outline()
        o.NewOutline()
        for x, y in zd["outline"]:
            o.Append(MM(ox + x), MM(oy + y))
        board.Add(z)
    return f"{len(data['tracks'])} tracks, {len(data['vias'])} vias, {len(data['zones'])} zones"


def preroute(board, spec):
    """Route the design's short, critical connections before the autorouter does the rest.

    Each entry joins pad A to pad B: the track leaves A straight out along the pad's long axis,
    away from its part, and then goes to B by the first of three shapes (direct, or a dog-leg
    either way) that clears every other net's pads and tracks. Returns (routed, skipped).
    """
    r = spec["rules"]
    routed = skipped = 0
    for item in spec.get("preroutes", []):
        (ra, pa), (rb, pb), width = item["a"], item["b"], MM(item.get("width", 0.2))
        fa, fb = board.FindFootprintByReference(ra), board.FindFootprintByReference(rb)
        pad_a = next(p for p in fa.Pads() if p.GetNumber() == pa)
        pad_b = next(p for p in fb.Pads() if p.GetNumber() == pb)
        net = pad_a.GetNet()
        if pad_b.GetNetCode() != net.GetNetCode():
            raise SystemExit(f"preroute {ra}.{pa} -> {rb}.{pb}: pads are on different nets")
        ca, cb = pad_a.GetPosition(), pad_b.GetPosition()
        bb = pad_a.GetBoundingBox()
        horizontal = bb.GetWidth() >= bb.GetHeight()
        centre = fa.GetPosition()
        if horizontal:
            sign = 1 if ca.x >= centre.x else -1
            esc = P.VECTOR2I(int(ca.x + sign * (bb.GetWidth() / 2 + MM(0.35))), ca.y)
        else:
            sign = 1 if ca.y >= centre.y else -1
            esc = P.VECTOR2I(ca.x, int(ca.y + sign * (bb.GetHeight() / 2 + MM(0.35))))
        keep = int(width / 2 + MM(r["clearance"] + 0.02))
        others = [(pad.GetBoundingBox(), pad.GetNetCode()) for fp in board.GetFootprints() for pad in fp.Pads()]
        others += [(t.GetBoundingBox(), t.GetNetCode()) for t in board.GetTracks()]

        def clear(p0, p1):
            n = max(2, int(((p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2) ** 0.5 / MM(0.05)))
            for k in range(n + 1):
                q = P.VECTOR2I(int(p0.x + (p1.x - p0.x) * k / n), int(p0.y + (p1.y - p0.y) * k / n))
                box = _box(q, keep)
                if any(ob.Intersects(box) and code != net.GetNetCode() for ob, code in others):
                    return False
                if _in_fiducial_keepout(spec, q, keep):
                    return False
            return True

        shapes = [[esc, cb], [esc, P.VECTOR2I(cb.x, esc.y), cb], [esc, P.VECTOR2I(esc.x, cb.y), cb]]
        for shape in shapes:
            pts = [ca] + shape
            if all(clear(pts[i], pts[i + 1]) for i in range(1, len(pts) - 1)):
                for i in range(len(pts) - 1):
                    if pts[i] == pts[i + 1]:
                        continue
                    t = P.PCB_TRACK(board)
                    t.SetStart(pts[i])
                    t.SetEnd(pts[i + 1])
                    t.SetWidth(width)
                    t.SetLayer(P.F_Cu)
                    t.SetNet(net)
                    board.Add(t)
                routed += 1
                break
        else:
            skipped += 1
            print(f"  preroute {ra}.{pa} -> {rb}.{pb}: no clear path, left to the router")
    return routed, skipped


FIDUCIAL_KEEPOUT = "eos-fiducial-keepout"


def _fiducial_obstacles(board, spec, side):
    """What a fiducial on ``side`` ("F" or "B") must keep its copper-free square off, as (x0, y0, x1,
    y1) mm boxes: the courtyards and silkscreen of that side's parts, every pad on that side and every
    drilled pad, the side's board texts, copper already laid (reference copper, pre-routes) and the
    design's keep-outs."""
    cu, crtyd, silk = (P.F_Cu, P.F_CrtYd, P.F_SilkS) if side == "F" else (P.B_Cu, P.B_CrtYd, P.B_SilkS)

    def mm_box(b):
        return (P.ToMM(b.GetX()), P.ToMM(b.GetY()), P.ToMM(b.GetRight()), P.ToMM(b.GetBottom()))

    out = []
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(crtyd)
        if cy.OutlineCount():
            out.append(mm_box(cy.BBox()))
        for item in fp.GraphicalItems():
            if item.GetLayer() == silk:
                out.append(mm_box(item.GetBoundingBox()))
        for pad in fp.Pads():
            if pad.IsOnLayer(cu) or pad.HasHole():
                out.append(mm_box(pad.GetBoundingBox()))
    for d in board.GetDrawings():
        if d.GetLayer() == silk:
            out.append(mm_box(d.GetBoundingBox()))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.GetLayer() == cu:
            out.append(mm_box(t.GetBoundingBox()))
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetLayer() == cu:
            out.append(mm_box(z.GetBoundingBox()))
    out += [tuple(k[:4]) for k in spec.get("copper_keepouts", []) + spec.get("router_keepouts", [])
            + spec.get("pour_keepouts", [])]
    return out


def _silk_obstacles(board, item, items=None):
    """What silkscreen ``item`` (a board text) must keep off: every pad of its side and every drilled
    pad, grown by SILK_PAD_GAP, as boxes; and every other silkscreen item on its layer (board texts and
    shapes, footprint graphics and visible footprint texts), as {uuid: box}. ``items``, a dict when
    given, also receives those items themselves by uuid."""
    layer = item.GetLayer()
    cu = P.B_Cu if layer == P.B_SilkS else P.F_Cu
    gap = MM(fabrication.SILK_PAD_GAP)
    pads, silk = [], {}
    items = {} if items is None else items
    own = item.m_Uuid.AsString()
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(cu) or pad.HasHole():
                b = pad.GetBoundingBox()
                pads.append(P.BOX2I(P.VECTOR2I(b.GetX() - gap, b.GetY() - gap),
                                    P.VECTOR2I(b.GetWidth() + 2 * gap, b.GetHeight() + 2 * gap)))
        for g in list(fp.GraphicalItems()) + [fp.Reference(), fp.Value()]:
            if g.GetLayer() == layer and (not hasattr(g, "IsVisible") or g.IsVisible()):
                silk[g.m_Uuid.AsString()] = g.GetBoundingBox()
                items[g.m_Uuid.AsString()] = g
    for d in board.GetDrawings():
        if d.GetLayer() == layer and d.m_Uuid.AsString() != own:
            silk[d.m_Uuid.AsString()] = d.GetBoundingBox()
            items[d.m_Uuid.AsString()] = d
    return pads, silk


def _strokes_touch(item, others):
    """True when ``item``'s strokes touch any of ``others`` (silkscreen on its layer), as KiCad's DRC
    sees silk over silk: their real shapes, not their boxes."""
    shape = item.GetEffectiveShape(item.GetLayer())
    return any(shape.Collide(o.GetEffectiveShape(item.GetLayer()), 0) for o in others)


def _silk_clear(spec, item, pads, silk, allowed):
    """True when ``item`` keeps SILK_PAD_GAP off every pad, SILK_EDGE_GAP inside the outline, and off
    every other silkscreen item but those in ``allowed``."""
    b = item.GetBoundingBox()
    corners = [P.VECTOR2I(x, y) for x in (b.GetX(), b.GetRight()) for y in (b.GetY(), b.GetBottom())]
    plain = dict(spec, copper_keepouts=[], fiducial_keepouts=[])
    return all(_inside(plain, c, MM(fabrication.SILK_EDGE_GAP)) for c in corners) \
        and not any(p.Intersects(b) for p in pads) \
        and not any(box.Intersects(b) for uid, box in silk.items() if uid not in allowed)


def fit_text(board, spec, item, t, pending=()):
    """Fit a silkscreen line the generator sizes (the identity line, the ownership lines): at least
    SILK_MIN_TEXT high, clear of every pad of its side and every drilled pad by SILK_PAD_GAP, inside
    the outline by SILK_EDGE_GAP, and off any other silkscreen that its design line (``design_text`` at
    ``design_size``, where the designer checked it) did not already touch (and whose strokes, not just
    boxes, it then keeps off: a larger line can reach them); the generator lines still to
    be fitted (``pending``, uuids) are not in the way yet, they fit round this one. Tried where the
    design put it, then moved (fabrication.silk_moves: up or down by up to 2 mm, then also up to 3 mm
    sideways), for each of its ``variants`` (the identity line shortens: fabrication.identity_variants),
    and last with narrower characters (fabrication.SILK_WIDTHS), all with the preferred 1:6 stroke and
    then, only if nothing fits, again at the 0.15 mm minimum; the height never goes down. A line that
    fits nowhere stops the build: fabs clip silkscreen off pads, and KiCad reports silk over
    copper only as a warning. Returns (the text placed, a description of where it went)."""
    items = {}
    pads, silk = _silk_obstacles(board, item, items)
    item.SetText(t.get("design_text") or t["text"])                   # what the designer checked, as drawn
    item.SetTextSize(v(t["design_size"], t["design_size"]))
    item.SetTextThickness(MM(fabrication.silk_stroke(t["design_size"], t.get("bold", False))))
    touched = {uid for uid, box in silk.items() if box.Intersects(item.GetBoundingBox())} if t.get("design_text") else set()
    # what the design line's box touched may stay box to box with the larger line, never stroke to stroke
    near = [items[uid] for uid in touched - set(pending)]
    allowed = touched | set(pending)
    preferred = fabrication.silk_stroke(t["size"], t.get("bold", False))
    # JLCPCB's preferred 1:6 stroke first; only a line that fits nowhere with it keeps the 0.15 mm minimum
    for stroke in [preferred] + ([fabrication.SILK_MIN_STROKE] if preferred > fabrication.SILK_MIN_STROKE else []):
        item.SetTextThickness(MM(stroke))
        for width in fabrication.SILK_WIDTHS:
            item.SetTextSize(v(t["size"] * width, t["size"]))            # the height stays t["size"]
            for words in t.get("variants", [t["text"]]):
                item.SetText(words)
                for dx, dy in fabrication.silk_moves():
                    item.SetPosition(v(t["x"] + dx, t["y"] + dy))
                    if _silk_clear(spec, item, pads, silk, allowed) and not _strokes_touch(item, near):
                        narrow = "" if width == 1.0 else f" ({width:g} wide)"
                        thin = "" if stroke == preferred else f" ({stroke:g} stroke: none fits at {preferred:g})"
                        return words, (f"{words!r} {t['size']} mm{narrow}{thin} at "
                                       f"({round(t['x'] + dx, 2)}, {round(t['y'] + dy, 2)})")
    raise SystemExit(f"silkscreen line {t['text']!r} at {t['size']} mm clears no pad, edge or other silkscreen "
                     f"within 2 mm up or down and 3 mm sideways of ({t['x']}, {t['y']}), even "
                     f"{min(fabrication.SILK_WIDTHS):g} wide; move the design's line")


def place_labels(board, spec):
    """Silkscreen labels (BENCH-READY A4, C1): each connector pin the design's ``pin_labels`` names, and
    each test pad (its value, the rail name), at fabrication.SILK_MIN_TEXT on the silkscreen of the pad's
    side, beside the pad where it clears every pad, the board edge, every other silkscreen, every other
    part's courtyard and every fiducial square (fabrication.label_spots). A through-hole pin whose top
    has no room is labelled on the bottom silkscreen instead (mirrored, so it reads from below; the pin
    is there too), and is listed in ``spec["labels_on_back"]``. A test pad whose rail name has no room
    gets its shorter reference ("TP5") instead, which the README's bring-up section keys to its rail
    (stage-2 review n3), listed in ``spec["labels_as_ref"]``. A label that fits nowhere is left out and
    reported (``spec["labels_skipped"]``); the README names those test pads as unlabelled. Returns
    (placed, skipped)."""
    jobs = [(ref, pad, label, None) for ref, labels in spec.get("pin_labels", {}).items() for pad, label in labels.items()]
    jobs += [(p["ref"], "1", p["value"], p["ref"]) for p in spec["parts"] if p.get("test_pad")]
    placed, skipped, back, as_ref = 0, [], [], []
    for ref, number, label, fallback in jobs:
        fp = board.FindFootprintByReference(ref)
        pad = next((q for q in fp.Pads() if q.GetNumber() == number), None)
        if pad is None:
            skipped.append(f"{ref}.{number} {label}: no such pad")
            continue
        bottom = fp.GetLayer() == P.B_Cu and pad.GetAttribute() == P.PAD_ATTRIB_SMD
        sides = [bottom] + ([not bottom] if pad.HasHole() else [])
        xs = [q.GetPosition().x for q in fp.Pads()]
        ys = [q.GetPosition().y for q in fp.Pads()]
        row = "" if len(xs) < 2 else ("horizontal" if max(xs) - min(xs) >= max(ys) - min(ys) else "vertical")
        b = pad.GetBoundingBox()
        box = (P.ToMM(b.GetX()), P.ToMM(b.GetY()), P.ToMM(b.GetRight()), P.ToMM(b.GetBottom()))
        tries = [(on_bottom, label) for on_bottom in sides]
        if fallback and fallback != label:
            tries += [(on_bottom, fallback) for on_bottom in sides]
        for on_bottom, words in tries:
            if _place_label(board, spec, ref, words, on_bottom, box, row):
                placed += 1
                if on_bottom and not bottom:
                    back.append(f"{ref}.{number} {words}")
                if words != label:
                    as_ref.append(f"{ref}.{number} {label}: {words}")
                break
        else:
            skipped.append(f"{ref}.{number} {label}")
    spec["labels_placed"], spec["labels_skipped"], spec["labels_on_back"] = placed, skipped, back
    spec["labels_as_ref"] = as_ref
    return placed, skipped


def _place_label(board, spec, ref, label, bottom, box, row):
    """One label on the bottom (``bottom``) or top silkscreen at the first of fabrication.label_spots
    round the pad box ``box`` that is clear (see place_labels); True when it went down, else the text
    is removed again."""
    layer, crtyd = (P.B_SilkS, P.B_CrtYd) if bottom else (P.F_SilkS, P.F_CrtYd)
    item = text(board, label, 0, 0, fabrication.SILK_MIN_TEXT, layer, 0.0, False, bottom)
    bb = item.GetBoundingBox()
    w, h = P.ToMM(bb.GetWidth()), P.ToMM(bb.GetHeight())
    pads, silk = _silk_obstacles(board, item)
    for other in board.GetFootprints():
        if other.GetReference() != ref:
            other.BuildCourtyardCaches()
            cy = other.GetCourtyard(crtyd)
            if cy.OutlineCount():
                silk["crtyd/" + other.GetReference()] = cy.BBox()
    for i, k in enumerate(spec.get("fiducial_keepouts", [])):
        silk[f"fiducial/{i}"] = P.BOX2I(v(k[0], k[1]), P.VECTOR2I(MM(k[2] - k[0]), MM(k[3] - k[1])))
    for x, y, angle in fabrication.label_spots(box, row, w, h):
        item.SetTextAngleDegrees(angle)
        item.SetPosition(v(x, y))
        if _silk_clear(spec, item, pads, silk, set()):
            return True
    _remove(board, item)
    return False


def place_fiducials(board, spec):
    """Fiducials on every side the assembler populates (fabrication.carries_smd_parts): positions from
    the design's ``fiducials`` option for a side it names, else three chosen near three corners, or two
    diagonally opposite where three do not fit (the reason goes into the spec's ``fiducial_notes``).
    Each is a board-only footprint (no schematic symbol, no BOM line, in the placement file) with a
    rule area round it that no track, via or pour may enter; the square also goes into the spec, so
    every later step's own copper keeps out. Returns [(reference, side, x, y)]."""
    def paste(pad):
        return pad.IsOnLayer(P.F_Paste) or pad.IsOnLayer(P.B_Paste)
    sides = [s for s, layer in (("F", P.F_Cu), ("B", P.B_Cu))
             if any(fp.GetLayer() == layer and fabrication.carries_smd_parts(
                 fp.IsDNP(), fp.IsExcludedFromPosFiles(), [(p.GetAttribute() == P.PAD_ATTRIB_SMD, paste(p)) for p in fp.Pads()])
                 for fp in board.GetFootprints())]
    given = spec.get("fiducials", {})
    sides += [s for s in given if s not in sides]
    lib, name = fabrication.FIDUCIAL_FOOTPRINT.split(":")
    placed = []
    for side in ("F", "B"):
        if side not in sides:
            continue
        obstacles = _fiducial_obstacles(board, spec, side)
        args = (spec["width"], spec["height"], spec["corner_radius"])
        if side in given:
            points = [tuple(p) for p in given[side]]
            problems = fabrication.fiducial_problems(points, *args, obstacles)
            if problems:
                raise SystemExit(f"fiducials on {side} from the design: " + "; ".join(problems))
        else:
            try:
                points, note = fabrication.choose_fiducials(*args, obstacles)
            except ValueError as e:
                raise SystemExit(f"{side} side: {e}")
            if note:
                spec.setdefault("fiducial_notes", {})[side] = note
                print(f"  fiducials on {side}: {note}")
        for x, y in points:
            fp = P.FootprintLoad(str(Path(spec["footprint_dir"]) / f"{lib}.pretty"), name)
            fp.SetFPIDAsString(fabrication.FIDUCIAL_FOOTPRINT)
            ref = f"FID{len(placed) + 1}"
            fp.SetReference(ref)
            fp.SetValue("Fiducial")
            board.Add(fp)
            fp.SetPosition(v(x, y))
            if side == "B":
                fp.Flip(fp.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetBoardOnly(True)           # not in the schematic: parity leaves it alone
            fp.SetExcludedFromBOM(True)     # not a BOM line, but in the placement file
            fp.Reference().SetLayer(P.B_Fab if side == "B" else P.F_Fab)
            x0, y0, x1, y1 = fabrication.fiducial_box(x, y)
            area = P.ZONE(board)
            area.SetIsRuleArea(True)
            area.SetLayer(P.F_Cu if side == "F" else P.B_Cu)
            area.SetZoneName(FIDUCIAL_KEEPOUT)
            area.SetDoNotAllowTracks(True)
            area.SetDoNotAllowVias(True)
            area.SetDoNotAllowZoneFills(True)
            area.SetDoNotAllowPads(False)
            area.SetDoNotAllowFootprints(False)
            o = area.Outline()
            o.NewOutline()
            for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                o.Append(MM(px), MM(py))
            board.Add(area)
            spec.setdefault("fiducial_keepouts", []).append([x0, y0, x1, y1, side])
            placed.append((ref, side, x, y))
    spec["fiducials_placed"] = [list(p) for p in placed]
    return placed


def place(spec, pcb_path, dsn_path):
    board = P.CreateEmptyBoard()
    rules(board, spec)
    outline(board, spec["width"], spec["height"], spec["corner_radius"])
    nets = {"": board.GetNetInfo().GetNetItem(0)}
    for name in spec["nets"]:
        item = P.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    for part in spec["parts"]:
        lib, name = part["footprint"].split(":", 1)
        lib_dir = Path(spec.get("local_footprints", {}).get(lib, Path(spec["footprint_dir"]) / f"{lib}.pretty"))
        fp = P.FootprintLoad(str(lib_dir), name)
        if fp is None:
            raise SystemExit(f"{part['ref']}: footprint {part['footprint']} not found")
        fp.SetFPIDAsString(part["footprint"])
        if part.get("model"):
            # the part fitted differs in shape from the footprint's model (a socket on a header's pads)
            path, (mx, my, mz) = part["model"]
            m = P.FP_3DMODEL()
            m.m_Filename = path
            m.m_Offset = P.VECTOR3D(mx, my, mz)
            fp.Models().clear()
            fp.Models().push_back(m)
        fp.SetReference(part["ref"])
        fp.SetValue(part["value"])
        fp.SetPath(P.KIID_PATH("/" + part["uuid"]))
        fp.SetSheetname("Root")
        fp.SetSheetfile(spec["name"] + ".kicad_sch")
        board.Add(fp)
        fp.SetPosition(v(part["x"], part["y"]))
        fp.SetOrientationDegrees(part["rot"])
        if part["side"] == "B":
            fp.Flip(fp.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
        if part.get("dnp"):
            fp.SetDNP(True)
        # the footprint follows its symbol, as KiCad's own Update PCB from Schematic does: a library
        # test point excludes itself from the BOM while its symbol counts it, a parity difference
        fp.SetExcludedFromBOM(not part.get("in_bom", True))
        for key, val in part.get("fields", {}).items():
            fp.SetField(key, val)
            field = fp.GetField(key)
            if field is not None:           # data for the BOM and parity check, not silkscreen text
                field.SetVisible(False)
                field.SetLayer(P.B_Fab if part["side"] == "B" else P.F_Fab)
        # Reference designators go on the assembly drawing; silkscreen keeps outlines only.
        fp.Reference().SetLayer(P.B_Fab if part["side"] == "B" else P.F_Fab)
        for pad in fp.Pads():
            net = part["pads"].get(pad.GetNumber())
            if net:
                pad.SetNet(nets[net])
    placed_texts = [(t, text(board, t["text"], t["x"], t["y"], t["size"], getattr(P, t.get("layer", "F_SilkS")),
                             t.get("angle", 0.0), t.get("bold", False), t.get("mirror", False)))
                    for t in spec.get("texts", [])]
    # the generator's own lines, the ownership lines first and the identity line last, each fitted
    # against everything already on the board but the generator lines after it, which then fit round it
    # (recorded in build-report.json)
    fits = sorted([pt for pt in placed_texts if pt[0].get("fit")], key=lambda pt: bool(pt[0].get("identity")))
    for i, (t, item) in enumerate(fits):
        words, where = fit_text(board, spec, item, t, {later.m_Uuid.AsString() for _, later in fits[i + 1:]})
        spec.setdefault("silk_fits", []).append(where)
        if t.get("identity"):
            spec["identity_fit"], spec["identity_text"] = where, words
        print(f"silkscreen: {where}")
    tb = board.GetTitleBlock()       # as the schematic's: title, date, revision, owner and licence
    tb.SetTitle(spec["title_block"]["title"])
    tb.SetDate(spec["title_block"]["date"])
    tb.SetRevision(spec["title_block"]["rev"])
    tb.SetCompany(spec["title_block"]["company"])
    for i, line in enumerate(spec["title_block"]["comments"]):
        tb.SetComment(i, line)
    # Inner planes go in before routing: the autorouter then joins each plane net's pads to
    # its plane with a via instead of routing them as tracks.
    for pl in spec.get("planes", []):
        layer = getattr(P, pl["layer"].replace(".", "_"))
        board.SetLayerType(layer, P.LT_POWER)
        zone(board, nets[pl["net"]], layer, spec["width"], spec["height"])
    if spec.get("reference_copper"):
        print(f"reference copper: {reference_copper(board, spec, nets)}")
    if spec.get("preroutes"):
        done, skipped = preroute(board, spec)
        print(f"pre-routed {done} critical connection(s), {skipped} left to the router")
    # A tight bus is routed first, in the order given, the way a designer lays it by hand: the
    # autorouter, left to pick its own order, can box one of its lines in. Locked, so it stays.
    # Before the plane fan-out, so the fan-out's vias fit around these lines, not across them.
    # Fine-pitch connector pads get their plane vias first: once the priority lines are in, a
    # ground pad between two signal pads has nowhere left for one.
    early = set(spec.get("escape_footprints", []))
    if early and spec.get("planes"):
        # into the channel between the pad rows, as Raspberry Pi's CM5 IO Board does: the outward
        # side stays free for the signal pads' escapes (see maze)
        placed, left = fanout(board, spec, only=early, inward=True)
        print(f"plane fan-out at {sorted(early)}: {placed} vias, {left} pads left to the router")
    # Parts named in fanout_first get their plane vias before the priority routes, which then go
    # round them: a supply route laid first can box a decoupling capacitor's via spots in.
    first = set(spec.get("fanout_first", [])) - early      # an escape footprint is fanned out once, inward
    if first:
        placed, left = fanout(board, spec, only=first)
        print(f"plane fan-out first at {sorted(first)}: {placed} vias, {left} pads left to the router")
    # A line with an escape in the reference copper leaves the chip on that escape first.
    escapes = {}
    if spec.get("reference_copper"):
        ref = spec["reference_copper"]
        ox, oy = ref["origin"]
        for e in json.loads(Path(ref["file"]).read_text()).get("escapes", []):
            escapes.setdefault(e["net"], []).append(e)
    for route in spec.get("priority_routes", []):
        (ra, pa), (rb, pb) = route[0], route[1]
        join, width = fabrication.route_options(route)      # "join", and a width in mm for this route alone
        pad_a = next(p for p in board.FindFootprintByReference(ra).Pads() if p.GetNumber() == pa)
        pad_b = next(p for p in board.FindFootprintByReference(rb).Pads() if p.GetNumber() == pb)
        net, start, laid = pad_a.GetNet(), pad_a.GetPosition(), []
        # only a route that starts at the escape's own pin takes it, and only once
        own = [e for e in escapes.pop(net.GetNetname(), [])]
        if own and not any(pad_a.HitTest(v(ox + x, oy + y), 0) for e in own for x, y in (e["a"], e["b"])):
            escapes[net.GetNetname()] = own
            own = []
        for e in own:
            laid.append(_track(board, net, v(ox + e["a"][0], oy + e["a"][1]), v(ox + e["b"][0], oy + e["b"][1]),
                               MM(e["w"]), getattr(P, e["layer"].replace(".", "_"))))
        laid = [t for t in laid if t is not None]      # a segment cut to nothing at the ring's edge
        if laid:
            # the escape's far end: the end of its chain furthest from the pad it starts at
            ends = [q for t in laid for q in (t.GetStart(), t.GetEnd())]
            start = max(ends, key=lambda q: (q.x - start.x) ** 2 + (q.y - start.y) ** 2)
        got = maze(board, spec, net, start, pad_b.GetPosition(), MM(width) if width else track_width(spec, net), join=join)
        if not got:
            raise SystemExit(f"priority route {ra}.{pa} -> {rb}.{pb}: no path")
        for item in laid + got:
            if item is not None:
                item.SetLocked(True)
        print(f"priority route {ra}.{pa} -> {rb}.{pb} ({net.GetNetname()}): "
              f"{len(laid)} escape segment(s) from the reference, then {len(got)} item(s)")
    # Fiducials after the reference copper, pre-routes and priority routes, the copper a designer lays
    # first (they take the free spots round it), and before the main fan-out, which then keeps its vias
    # out of the fiducials' squares, as every later step does.
    print(f"fiducials: {place_fiducials(board, spec)}")
    placed, left = fanout(board, spec, exclude=early | first)   # two layers: the exposed pads' vias only
    if placed or left:
        print(f"plane fan-out: {placed} vias, {left} pads left to the router")
    labelled, unlabelled = place_labels(board, spec)          # after the fiducials: labels keep off their squares
    print(f"labels: {labelled} placed, {len(unlabelled)} with no room: {unlabelled}")
    for x0, y0, x1, y1 in spec.get("copper_keepouts", []):
        copper_keepout(board, [(MM(x0), MM(y0)), (MM(x1), MM(y0)), (MM(x1), MM(y1)), (MM(x0), MM(y1))])
    for x0, y0, x1, y1, layer in spec.get("pour_keepouts", []):
        pour_keepout(board, getattr(P, layer.replace(".", "_")),
                     [(MM(x0), MM(y0)), (MM(x1), MM(y0)), (MM(x1), MM(y1)), (MM(x0), MM(y1))])
    if board.Zones():
        P.ZONE_FILLER(board).Fill(board.Zones())
    P.SaveBoard(pcb_path, board)
    # the fab's stack-up, written into the saved file: KiCad 10's Python does not wrap BOARD_STACKUP
    saved = Path(pcb_path)
    saved.write_text(fabrication.insert_stackup(saved.read_text(encoding="utf-8"), spec["stackup"]), encoding="utf-8")
    # From here on the changes reach the router's input only, never the saved board.
    # Freerouting works on a grid and can leave a track a fraction of a micrometre inside the
    # clearance (0.1491 mm against 0.15 mm, on EoS ESP32 DevKit). The router sees a little more
    # clearance than the board's rules: enough for that rounding plus the 0.005 mm a side that
    # finish() adds when it widens a 0.09 mm neck to 0.1 mm. DRC checks the board's own rules.
    ns = board.GetDesignSettings().m_NetSettings
    classes = ns.GetNetclasses()
    for nc in [ns.GetDefaultNetclass(), *[classes[name] for name in classes]]:
        nc.SetClearance(nc.GetClearance() + MM(ROUTER_MARGIN))
    ns.RecomputeEffectiveNetclasses()
    # Keep-outs: the board's own (under a chip whose underside copper is fixed), and each
    # reference zone. Exported as they are, those zones would reach the router as solid planes
    # over their whole outline, overlapping each other and closing channels their copper leaves open.
    for k in spec.get("router_keepouts", []):
        x0, y0, x1, y1 = k[:4]
        layer = P.B_Cu if len(k) > 4 and k[4] == "B.Cu" else P.F_Cu
        _keepout(board, layer, [(MM(x0), MM(y0)), (MM(x1), MM(y0)), (MM(x1), MM(y1)), (MM(x0), MM(y1))])
    for z in [z for z in board.Zones() if z.GetZoneName() == POUR_KEEPOUT]:
        _remove(board, z)                # KiCad would export a fill-only rule area as a full keep-out
    for z in [z for z in board.Zones() if z.GetZoneName() == REFERENCE_ZONE]:
        o = z.Outline()
        _keepout(board, z.GetLayer(), [(o.CVertex(i).x, o.CVertex(i).y) for i in range(o.TotalVertices())])
        _remove(board, z)
    if not P.ExportSpecctraDSN(board, dsn_path):
        raise SystemExit("Specctra DSN export failed")
    # Freerouting may not put a via on a surface pad: 2.4.1's default, stated here so that a
    # later default cannot change it (the Specctra control rule)
    dsn = Path(dsn_path).read_text()
    if "(via_at_smd" not in dsn:
        if dsn.count("(structure") != 1:
            raise SystemExit("unexpected DSN layout: no single (structure scope")
        Path(dsn_path).write_text(dsn.replace("(structure", "(structure\n    (control\n      (via_at_smd off)\n    )", 1))
    print(f"placed {len(spec['parts'])} footprints, {len(spec['nets'])} nets -> {pcb_path}, {dsn_path}")


def stitch(board, net, spec, pitch=2.54, margin=1.2):
    """GND vias on a grid wherever no other net's copper is near: they join the top and bottom
    pours into one ground, so no island of top-layer ground is left unconnected."""
    r = spec["rules"]
    keep = MM(r["via"] / 2 + r["clearance"] + 0.15)
    obstacles = []
    for t in board.GetTracks():
        if t.GetNetCode() != net.GetNetCode():
            obstacles.append(t.GetBoundingBox())
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            # a surface pad of any net, its own included: no via in a pad (a bottom-side part
            # has no front courtyard to keep the grid off it)
            if pad.GetNetCode() != net.GetNetCode() or pad.GetAttribute() in (P.PAD_ATTRIB_NPTH, P.PAD_ATTRIB_SMD):
                obstacles.append(pad.GetBoundingBox())
        for side in (P.F_CrtYd, P.B_CrtYd):
            cy = fp.GetCourtyard(side)
            if cy.OutlineCount():
                obstacles.append(cy.BBox())
    placed = 0
    holes = _holes(board)
    w, h = spec["width"], spec["height"]
    y = margin
    while y <= h - margin:
        x = margin
        while x <= w - margin:
            c = v(x, y)
            box = P.BOX2I(P.VECTOR2I(c.x - keep, c.y - keep), P.VECTOR2I(2 * keep, 2 * keep))
            if not _inside(spec, c, MM(r["edge_clearance"] + r["via"] / 2 + 0.1)) or _in_pour_keepout(spec, c, keep):
                x += pitch
                continue
            if not any(o.Intersects(box) for o in obstacles) and _hole_free(holes, c, MM(r["drill"])):
                holes.append((c, MM(r["drill"]) // 2))
                via = P.PCB_VIA(board)
                via.SetPosition(c)
                via.SetWidth(MM(r["via"]))
                via.SetDrill(MM(r["drill"]))
                via.SetNet(net)
                board.Add(via)
                obstacles.append(box)
                placed += 1
            x += pitch
        y += pitch
    return placed


def join_all_fragments(board, spec, filler):
    """join_fragments on every poured net, refilling after each round, up to three rounds a net. Run
    after the pours are first filled (finish) and again after each repair, whose new tracks can cut a
    pour into pieces that no via reaches."""
    for z in spec.get("zones", []):
        net = board.FindNet(z["net"])
        for _ in range(3):
            added = join_fragments(board, net, spec)
            if not added:
                break
            print(f"fragment vias on {z['net']}: {added}")
            filler.Fill(board.Zones())


def join_fragments(board, net, spec):
    """Give every outer-layer pour fragment of ``net`` that has no via or through-hole pad a
    via into the inner plane: a fragment whose only link is a surface pad (VREG_PGND, say)
    would otherwise be an unconnected island of ground."""
    r = spec["rules"]
    radius = MM(r["via"] / 2 + 0.05)
    anchors = [t.GetPosition() for t in board.GetTracks()
               if t.GetClass() == "PCB_VIA" and t.GetNetCode() == net.GetNetCode()]
    pads, smd = [], []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net.GetNetCode() and pad.GetAttribute() == P.PAD_ATTRIB_PTH:
                anchors.append(pad.GetPosition())
            pads.append(pad.GetBoundingBox())
            if pad.GetAttribute() == P.PAD_ATTRIB_SMD and not _exposed_pad(fp, pad):
                smd.append(pad.GetEffectiveShape(P.F_Cu if pad.IsOnLayer(P.F_Cu) else P.B_Cu))
    added = 0
    holes = _holes(board)
    reach = MM(r["via"] / 2 + r["clearance"])

    def clear_of_others(c):
        # a fragment can be U-shaped round another net's track: test the via's whole disk
        for t in board.GetTracks():
            if t.GetNetCode() == net.GetNetCode():
                continue
            if t.GetEffectiveShape(P.F_Cu if t.GetClass() == "PCB_VIA" else t.GetLayer()).Collide(c, reach):
                return False
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() != net.GetNetCode() and any(
                        pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(c, reach) for layer in (P.F_Cu, P.B_Cu)):
                    return False
        return True

    for z in board.Zones():
        if z.GetNetCode() != net.GetNetCode() or z.GetLayer() not in (P.F_Cu, P.B_Cu):
            continue
        polys = z.GetFilledPolysList(z.GetLayer())
        for i in range(polys.OutlineCount()):
            outline = polys.Outline(i)
            if any(outline.PointInside(a) for a in anchors):
                continue
            box = outline.BBox()
            step = MM(0.2)
            done = False
            y = box.GetY() + radius
            while y < box.GetBottom() - radius and not done:
                x = box.GetX() + radius
                while x < box.GetRight() - radius and not done:
                    c = P.VECTOR2I(int(x), int(y))
                    ring = [P.VECTOR2I(int(c.x + radius * dx), int(c.y + radius * dy))
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7))]
                    vb = P.BOX2I(P.VECTOR2I(c.x - radius, c.y - radius), P.VECTOR2I(2 * radius, 2 * radius))
                    if outline.PointInside(c) and all(outline.PointInside(q) for q in ring) \
                            and not any(pb.Intersects(vb) for pb in pads) and _hole_free(holes, c, MM(r["drill"])) \
                            and not _in_pour_keepout(spec, c, radius) and clear_of_others(c) \
                            and not _in_fiducial_keepout(spec, c, radius) \
                            and not any(sh.Collide(c, MM(r["via"] / 2 + VIA_PAD_GAP)) for sh in smd):
                        holes.append((c, MM(r["drill"]) // 2))
                        via = P.PCB_VIA(board)
                        via.SetPosition(c)
                        via.SetWidth(MM(r["via"]))
                        via.SetDrill(MM(r["drill"]))
                        via.SetNet(net)
                        board.Add(via)
                        anchors.append(c)
                        added += 1
                        done = True
                    x += step
                y += step
    return added


def _endpoint_layers(board, net, pt):
    """The outer copper layers of the net's item at ``pt``: a through-hole pad or via is on both."""
    near = MM(0.002)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net.GetNetCode() and abs(pad.GetPosition().x - pt.x) <= near \
                    and abs(pad.GetPosition().y - pt.y) <= near:
                return [layer for layer in (P.F_Cu, P.B_Cu) if pad.IsOnLayer(layer)]
    for t in board.GetTracks():
        if t.GetNetCode() != net.GetNetCode():
            continue
        if t.GetClass() == "PCB_VIA":
            if abs(t.GetPosition().x - pt.x) <= near and abs(t.GetPosition().y - pt.y) <= near:
                return [P.F_Cu, P.B_Cu]
        elif any(abs(e.x - pt.x) <= near and abs(e.y - pt.y) <= near for e in (t.GetStart(), t.GetEnd())):
            return [t.GetLayer()]
    return [P.F_Cu]


def maze(board, spec, net, a, b, width, join=False):
    """Join points ``a`` and ``b`` of ``net`` through the gaps the autorouter could not find.

    A grid search (A*, 0.05 mm cells, eight directions) on the two outer layers, with a via
    wherever one fits. Every other net's pads, tracks, vias and fixed zones are obstacles,
    grown by the clearance; the board's ground pours are not, since they are refilled around
    the new copper. The router keep-outs stay closed. Returns the tracks and vias it laid
    (an empty list when there is no way through).
    """
    import heapq
    import math

    r = spec["rules"]
    g = MM(0.05)
    margin = MM(0.04)      # more than half a cell's diagonal: a diagonal step between two blocked cells still clears
    hw, via_r = width // 2, MM(r["via"] / 2)
    clearance = MM(r["clearance"])
    edge = MM(r["edge_clearance"])
    reach = MM(4.0)
    bx0 = max(edge + via_r, min(a.x, b.x) - reach)
    by0 = max(edge + via_r, min(a.y, b.y) - reach)
    bx1 = min(MM(spec["width"]) - edge - via_r, max(a.x, b.x) + reach)
    by1 = min(MM(spec["height"]) - edge - via_r, max(a.y, b.y) + reach)
    x0 = a.x - ((a.x - bx0) // g) * g        # the grid passes through a
    y0 = a.y - ((a.y - by0) // g) * g
    nx, ny = int((bx1 - x0) // g) + 1, int((by1 - y0) // g) + 1
    layers = (P.F_Cu, P.B_Cu)
    track_block = [bytearray(nx * ny) for _ in layers]   # a track centre may not enter
    via_block = bytearray(nx * ny)                         # a via centre may not enter

    def cells(box):
        i0 = max(0, int((box.GetX() - x0) // g)); j0 = max(0, int((box.GetY() - y0) // g))
        i1 = min(nx - 1, int((box.GetRight() - x0) // g) + 1); j1 = min(ny - 1, int((box.GetBottom() - y0) // g) + 1)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                yield i, j, P.VECTOR2I(x0 + i * g, y0 + j * g)

    search = P.BOX2I(P.VECTOR2I(x0, y0), P.VECTOR2I(nx * g, ny * g))

    def stamp(shape, box, layer_ids, through):
        grow_t, grow_v = hw + clearance + margin, via_r + clearance + margin
        big = P.BOX2I(P.VECTOR2I(box.GetX() - grow_v, box.GetY() - grow_v),
                      P.VECTOR2I(box.GetWidth() + 2 * grow_v, box.GetHeight() + 2 * grow_v))
        if not big.Intersects(search):
            return
        for i, j, pt in cells(big):
            k = j * nx + i
            if shape(pt, grow_v):
                via_block[k] = 1
                if shape(pt, grow_t):
                    for li in layer_ids:
                        track_block[li][k] = 1

    code = net.GetNetCode()
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == code and code > 0:
                # its own net's pad: a track may join it, but no via may sit in a surface pad,
                # since solder wicks down an open barrel and starves the joint. A chip's exposed
                # pad is the exception: it takes vias by design (fanout).
                if pad.GetAttribute() == P.PAD_ATTRIB_SMD and not _exposed_pad(fp, pad):
                    layer = P.F_Cu if pad.IsOnLayer(P.F_Cu) else P.B_Cu
                    sh = pad.GetEffectiveShape(layer)
                    pb = pad.GetBoundingBox()   # not b: that is the route's far end
                    gap = via_r + MM(VIA_PAD_GAP) + margin
                    grown = P.BOX2I(P.VECTOR2I(pb.GetX() - gap, pb.GetY() - gap),
                                    P.VECTOR2I(pb.GetWidth() + 2 * gap, pb.GetHeight() + 2 * gap))
                    if grown.Intersects(search):
                        for i, j, pt in cells(grown):
                            if sh.Collide(pt, gap):
                                via_block[j * nx + i] = 1
                continue
            for li, layer in enumerate(layers):
                if pad.IsOnLayer(layer):
                    sh = pad.GetEffectiveShape(layer)
                    stamp(lambda pt, c, sh=sh: sh.Collide(pt, c), pad.GetBoundingBox(), [li], False)
            if pad.HasHole():
                hole = pad.GetEffectiveHoleShape()
                stamp(lambda pt, c, sh=hole: sh.Collide(pt, c - clearance + MM(r["hole_clearance"])),
                      pad.GetBoundingBox(), [0, 1], True)
    for t in board.GetTracks():
        if t.GetNetCode() == code:
            continue
        if t.GetClass() == "PCB_VIA":
            sh = t.GetEffectiveShape(P.F_Cu)
            stamp(lambda pt, c, sh=sh: sh.Collide(pt, c), t.GetBoundingBox(), [0, 1], True)
            continue
        if t.GetLayer() not in layers:
            continue
        li = layers.index(t.GetLayer())
        if not t.GetBoundingBox().Intersects(search):
            continue
        # a long track: stamp along it rather than over its whole bounding box
        st, en = t.GetStart(), t.GetEnd()
        n = max(1, int(((en.x - st.x) ** 2 + (en.y - st.y) ** 2) ** 0.5 // g))
        half = t.GetWidth() // 2
        for k in range(n + 1):
            c = P.VECTOR2I(int(st.x + (en.x - st.x) * k / n), int(st.y + (en.y - st.y) * k / n))
            stamp(lambda pt, cl, c=c, half=half: (pt.x - c.x) ** 2 + (pt.y - c.y) ** 2 <= (half + cl + MM(0.002)) ** 2,
                  _box(c, half), [li], False)
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() == code or z.GetZoneName() != REFERENCE_ZONE:
            continue
        li = layers.index(z.GetLayer()) if z.GetLayer() in layers else None
        if li is None:
            continue
        fl = z.GetFilledPolysList(z.GetLayer())
        stamp(lambda pt, c, fl=fl: fl.Collide(pt, c), z.GetBoundingBox(), [li], False)
    # Fine-pitch connectors keep every pad's way out: the channel between the pad rows is closed,
    # and a corridor straight out from each pad belongs to that pad's net alone. Without this the
    # shortest path hugs the pad ends, and the first lines routed seal their neighbours in.
    for ref in spec.get("escape_footprints", []):
        fp = board.FindFootprintByReference(ref)
        centre = fp.GetPosition()
        inner = []
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            long_x = bb.GetWidth() >= bb.GetHeight()
            c = pad.GetPosition()
            half_long = (bb.GetWidth() if long_x else bb.GetHeight()) // 2
            sign = 1 if ((c.x - centre.x) if long_x else (c.y - centre.y)) >= 0 else -1
            inner.append(P.VECTOR2I(c.x - sign * half_long, c.y) if long_x else P.VECTOR2I(c.x, c.y - sign * half_long))
            if pad.GetNetCode() == code:
                continue
            reach_c = MM(1.0)
            if long_x:
                x_a, x_b = sorted((c.x + sign * half_long, c.x + sign * (half_long + reach_c)))
                box = P.BOX2I(P.VECTOR2I(x_a, bb.GetY()), P.VECTOR2I(x_b - x_a, bb.GetHeight()))
            else:
                y_a, y_b = sorted((c.y + sign * half_long, c.y + sign * (half_long + reach_c)))
                box = P.BOX2I(P.VECTOR2I(bb.GetX(), y_a), P.VECTOR2I(bb.GetWidth(), y_b - y_a))
            stamp(lambda pt, cl, box=box: box.GetX() - cl <= pt.x <= box.GetRight() + cl
                  and box.GetY() - cl <= pt.y <= box.GetBottom() + cl, box, [layers.index(P.F_Cu)], False)
        xs, ys = [q.x for q in inner], [q.y for q in inner]
        channel = P.BOX2I(P.VECTOR2I(min(xs), min(ys)), P.VECTOR2I(max(xs) - min(xs), max(ys) - min(ys)))
        for i, j, pt in cells(channel):
            track_block[layers.index(P.F_Cu)][j * nx + i] = 1
    # outside the board outline (its rounded corners included) is closed to tracks and vias
    t_edge, v_edge = edge + hw + margin, edge + via_r + margin
    no_fiducials = dict(spec, fiducial_keepouts=[])
    for j in range(ny):
        for i in range(nx):
            pt = P.VECTOR2I(x0 + i * g, y0 + j * g)
            if not _inside(spec, pt, v_edge):              # a via spans every layer: any fiducial's square
                via_block[j * nx + i] = 1
                if not _inside(no_fiducials, pt, t_edge):
                    track_block[0][j * nx + i] = 1
                    track_block[1][j * nx + i] = 1
    # a fiducial's square closes tracks on its own layer only: its rule area is on that layer, and a
    # track on the other side may pass under it
    for k in spec.get("fiducial_keepouts", []):
        li = 0 if k[4] == "F" else 1
        grow = hw + margin
        box = P.BOX2I(P.VECTOR2I(MM(k[0]) - grow, MM(k[1]) - grow), P.VECTOR2I(MM(k[2] - k[0]) + 2 * grow, MM(k[3] - k[1]) + 2 * grow))
        if box.Intersects(search):
            for i, j, pt in cells(box):
                track_block[li][j * nx + i] = 1
    # drilled holes of any net, this one's included: a new via keeps HOLE_TO_HOLE from each
    for c, rad in _holes(board):
        reach_h = rad + MM(r["drill"]) // 2 + MM(HOLE_TO_HOLE) + margin
        for i, j, pt in cells(_box(c, reach_h)):
            if (pt.x - c.x) ** 2 + (pt.y - c.y) ** 2 < reach_h * reach_h:
                via_block[j * nx + i] = 1
    for k in spec.get("router_keepouts", []):
        x_0, y_0, x_1, y_1 = k[:4]
        li = 1 if len(k) > 4 and k[4] == "B.Cu" else 0
        box = P.BOX2I(v(x_0, y_0), P.VECTOR2I(MM(x_1 - x_0), MM(y_1 - y_0)))
        for i, j, pt in cells(box):
            track_block[li][j * nx + i] = 1
            via_block[j * nx + i] = 1

    def cell(pt):
        return int(round((pt.x - x0) / g)), int(round((pt.y - y0) / g))

    sa, sb = cell(a), cell(b)
    la, lb = _endpoint_layers(board, net, a), _endpoint_layers(board, net, b)
    goals = {(sb[0], sb[1], layers.index(l)) for l in lb}
    joinable = None
    if join:
        # Join mode: any copper the net already has counts as arrived (b only steers the search),
        # so a branch, such as an ESD part's pad, meets its line at the nearest point.
        joinable = [bytearray(nx * ny) for _ in layers]
        own = [pad for fp in board.GetFootprints() for pad in fp.Pads()
               if pad.GetNetCode() == code and not pad.HitTest(a, 0)]
        for pad in own:
            for li, layer in enumerate(layers):
                if pad.IsOnLayer(layer):
                    sh = pad.GetEffectiveShape(layer)
                    for i, j, pt in cells(pad.GetBoundingBox()):
                        if sh.Collide(pt, 0):
                            joinable[li][j * nx + i] = 1
        for t in board.GetTracks():
            if t.GetNetCode() != code:
                continue
            for li, layer in enumerate(layers):
                if t.GetClass() == "PCB_VIA" or t.GetLayer() == layer:
                    sh = t.GetEffectiveShape(layer)
                    for i, j, pt in cells(t.GetBoundingBox()):
                        if sh.Collide(pt, 0):
                            joinable[li][j * nx + i] = 1
    for (i, j), ls in ((sa, la), (sb, lb)):      # the end points sit in their own copper
        for l in ls:
            track_block[layers.index(l)][j * nx + i] = 0
    via_cost = int(spec.get("maze_via_cost_mm", 1.2) / 0.05)    # a via costs as much as this much track
    open_ = []
    best = {}
    for l in la:
        s0 = (sa[0], sa[1], layers.index(l))
        best[s0] = 0
        heapq.heappush(open_, (0, 0, s0, None))
    came = {}
    steps = [(1, 0, 10), (-1, 0, 10), (0, 1, 10), (0, -1, 10), (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14)]

    def h(i, j):
        dx, dy = abs(i - sb[0]), abs(j - sb[1])
        return 10 * max(dx, dy) + 4 * min(dx, dy)

    found = None
    expanded = 0
    while open_ and expanded < 3_000_000:
        f, cost, state, parent = heapq.heappop(open_)
        if state in came:
            continue
        came[state] = parent
        expanded += 1
        if state in goals or (joinable is not None and joinable[state[2]][state[1] * nx + state[0]]):
            found = state
            break
        i, j, l = state
        tb = track_block[l]
        for di, dj, c in steps:
            ni, nj = i + di, j + dj
            if not (0 <= ni < nx and 0 <= nj < ny) or tb[nj * nx + ni]:
                continue
            ns = (ni, nj, l)
            nc = cost + c
            if nc < best.get(ns, 1 << 60):
                best[ns] = nc
                heapq.heappush(open_, (nc + h(ni, nj), nc, ns, state))
        ns = (i, j, 1 - l)
        if not via_block[j * nx + i] and not track_block[1 - l][j * nx + i]:
            nc = cost + via_cost * 10
            if nc < best.get(ns, 1 << 60):
                best[ns] = nc
                heapq.heappush(open_, (nc + h(i, j), nc, ns, state))
    if found is None:
        print(f"  maze: no path for {net.GetNetname()} after {expanded} cells")
        return []
    path = []
    s_ = found
    while s_ is not None:
        path.append(s_)
        s_ = came[s_]
    path.reverse()

    def point(st):
        return P.VECTOR2I(x0 + st[0] * g, y0 + st[1] * g)

    # straight runs become one track each; a change of layer becomes a via
    added = []
    run_start = path[0]
    prev_dir = None
    for k in range(1, len(path)):
        p0, p1 = path[k - 1], path[k]
        if p1[2] != p0[2]:
            if run_start[:2] != p0[:2]:
                added.append(_track(board, net, point(run_start), point(p0), width, layers[p0[2]]))
            via = P.PCB_VIA(board)
            via.SetPosition(point(p0))
            via.SetWidth(MM(r["via"]))
            via.SetDrill(MM(r["drill"]))
            via.SetNet(net)
            board.Add(via)
            added.append(via)
            run_start, prev_dir = p1, None
            continue
        d = (p1[0] - p0[0], p1[1] - p0[1])
        if prev_dir is not None and d != prev_dir:
            added.append(_track(board, net, point(run_start), point(p0), width, layers[p0[2]]))
            run_start = p0
        prev_dir = d
    if run_start[:2] != path[-1][:2]:
        added.append(_track(board, net, point(run_start), point(path[-1]), width, layers[path[-1][2]]))
    added.append(_track(board, net, a, point(path[0]), width, layers[path[0][2]]))
    if path[-1][:2] == sb:                       # arrived at b itself, not at other copper of the net
        added.append(_track(board, net, point(path[-1]), b, width, layers[path[-1][2]]))
    return [item for item in added if item is not None] or [None]   # a one-cell path still counts as found


def _track(board, net, p0, p1, width, layer):
    if p0.x == p1.x and p0.y == p1.y:
        return None
    t = P.PCB_TRACK(board)
    t.SetStart(p0)
    t.SetEnd(p1)
    t.SetWidth(width)
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)
    return t


def _lift_near(board, spec, net, points, radius):
    """Remove the autorouter's tracks and vias of other signal nets that pass within ``radius``
    of any of ``points``: the local rip-up that frees a pin the autorouter boxed in. Locked
    copper and plane nets stay. Returns the removed items, so they can be put back."""
    plane_nets = {pl["net"] for pl in spec.get("planes", [])}
    lifted = []
    for t in list(board.GetTracks()):
        if t.IsLocked() or t.GetNetCode() in (0, net.GetNetCode()) or t.GetNetname() in plane_nets:
            continue
        if t.GetClass() == "PCB_VIA":
            near = any((t.GetPosition().x - q.x) ** 2 + (t.GetPosition().y - q.y) ** 2 <= radius ** 2 for q in points)
        else:
            st, en = t.GetStart(), t.GetEnd()
            dx, dy = en.x - st.x, en.y - st.y
            near = False
            for q in points:
                k = 0.0 if dx == 0 and dy == 0 else max(0.0, min(1.0, ((q.x - st.x) * dx + (q.y - st.y) * dy) / (dx * dx + dy * dy)))
                cx, cy = st.x + k * dx, st.y + k * dy
                near = near or (cx - q.x) ** 2 + (cy - q.y) ** 2 <= radius ** 2
        if near:
            _remove(board, t)
            lifted.append(t)
    return lifted


def _rejoin(board, spec, lifted, width):
    """Route each net that ``_lift_near`` cut back together, between the points where its
    lifted copper met copper that is still there. Returns (all joined, items added)."""
    added = []
    for code in sorted({t.GetNetCode() for t in lifted}):
        net = next(t.GetNet() for t in lifted if t.GetNetCode() == code)
        anchors = []
        for t in (t for t in lifted if t.GetNetCode() == code):
            ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
            for q in ends:
                still = any(pad.GetNetCode() == code and pad.HitTest(q, 0)
                            for fp in board.GetFootprints() for pad in fp.Pads()) or \
                        any(o.GetNetCode() == code and o.HitTest(q, 0) for o in board.GetTracks())
                if still and not any(abs(q.x - u.x) < MM(0.01) and abs(q.y - u.y) < MM(0.01) for u in anchors):
                    anchors.append(q)
        for k in range(len(anchors) - 1):
            got = maze(board, spec, net, anchors[k], anchors[k + 1], width)
            if not got:
                return False, added
            added += [item for item in got if item is not None]
    return True, added


def ripup(spec, pcb_path, clashes_path):
    """Lift one net's routed copper around each clearance clash KiCad's DRC found (the autorouter
    can leave a via 0.1 mm from another net's track), so the next repair round, which sees those
    connections open, routes them again with full clearance. Locked (reference) copper stays."""
    board = P.LoadBoard(pcb_path)
    clashes = json.loads(Path(clashes_path).read_text())
    lifted = 0

    def lift(net, pos):
        at, n = v(*pos), 0
        for t in list(board.GetTracks()):
            if t.IsLocked() or t.GetNetname() != net:
                continue
            box = t.GetBoundingBox()
            box.Inflate(MM(1.0))
            if box.Contains(at):
                _remove(board, t)
                n += 1
        return n

    def fixed(item):
        # the named item is locked copper: a locked via, or a locked track of its length, of its net at its spot
        at = v(*item["pos"])
        for t in board.GetTracks():
            via = t.GetClass() == "PCB_VIA"
            if t.IsLocked() and t.GetNetname() == item["net"] and via == item.get("via", False) \
                    and t.HitTest(at, MM(0.005)) and (via or abs(P.ToMM(t.GetLength()) - item.get("length", 0.0)) < 0.001):
                return True
        return False

    for c in clashes:
        # the named item, or what it clashes with when the named one is fixed copper (a locked fan-out via)
        lifted += fabrication.lift_with_fallback(c, lift, fixed)
    if lifted:
        P.ZONE_FILLER(board).Fill(board.Zones())
    P.SaveBoard(pcb_path, board)
    print(f"ripped up {lifted} item(s) at {len(clashes)} clearance clash(es)")


def repair(spec, pcb_path, pairs_path):
    """Close the connections the autorouter left open, as listed by KiCad's own DRC.

    For each unconnected pair: join the two points with a top-layer track (straight, or a
    dog-leg either way), if it clears every other net; failing that,
    if the net has an inner plane, give the pad end its own via into the plane; failing that,
    search for a path on both outer layers (``maze``); failing that, lift the autorouter's
    tracks of other nets next to the two ends and search again (``_lift_near``).
    """
    board = P.LoadBoard(pcb_path)
    r = spec["rules"]
    plane_nets = {pl["net"] for pl in spec.get("planes", [])}
    pairs = json.loads(Path(pairs_path).read_text())
    fixed = 0
    for pair in pairs:
        net = board.FindNet(pair["net"])
        if net is None:
            continue
        a = P.VECTOR2I(MM(pair["a"][0]), MM(pair["a"][1]))
        b = P.VECTOR2I(MM(pair["b"][0]), MM(pair["b"][1]))
        width = MM(0.2)
        keep = int(width / 2 + MM(r["clearance"] + 0.02))
        others = [(pad.GetBoundingBox(), pad.GetNetCode()) for fp in board.GetFootprints() for pad in fp.Pads()]
        others += [(t.GetBoundingBox(), t.GetNetCode()) for t in board.GetTracks()]

        def clear(p0, p1):
            n = max(2, int(((p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2) ** 0.5 / MM(0.05)))
            for k in range(n + 1):
                q = P.VECTOR2I(int(p0.x + (p1.x - p0.x) * k / n), int(p0.y + (p1.y - p0.y) * k / n))
                if any(ob.Intersects(_box(q, keep)) and code != net.GetNetCode() for ob, code in others):
                    return False
                if _in_fiducial_keepout(spec, q, keep):
                    return False
            return True

        done = False
        for shape in ([a, b], [a, P.VECTOR2I(b.x, a.y), b], [a, P.VECTOR2I(a.x, b.y), b]):
            if all(clear(shape[i], shape[i + 1]) for i in range(len(shape) - 1)):
                for i in range(len(shape) - 1):
                    if shape[i] == shape[i + 1]:
                        continue
                    t = P.PCB_TRACK(board)
                    t.SetStart(shape[i])
                    t.SetEnd(shape[i + 1])
                    t.SetWidth(width)
                    t.SetLayer(P.F_Cu)
                    t.SetNet(net)
                    board.Add(t)
                done = True
                break
        if not done and pair["net"] in plane_nets:
            via_r = MM(r["via"] / 2)
            vkeep = via_r + MM(r["clearance"] + 0.02)
            own_pads = [pad.GetEffectiveShape(P.F_Cu if pad.IsOnLayer(P.F_Cu) else P.B_Cu)
                        for fp in board.GetFootprints() for pad in fp.Pads()
                        if pad.GetNetCode() == net.GetNetCode() and pad.GetAttribute() == P.PAD_ATTRIB_SMD
                        and not _exposed_pad(fp, pad)]
            for end in (a, b):
                for rad in (0.6, 0.9, 1.2, 1.5):
                    for ang in range(0, 360, 30):
                        import math
                        pos = P.VECTOR2I(int(end.x + MM(rad) * math.cos(math.radians(ang))),
                                         int(end.y + MM(rad) * math.sin(math.radians(ang))))
                        if not _inside(spec, pos, MM(r["edge_clearance"] + r["via"] / 2 + 0.1)):
                            continue
                        if any(ob.Intersects(_box(pos, vkeep)) and code != net.GetNetCode() for ob, code in others):
                            continue
                        if any(sh.Collide(pos, via_r + MM(VIA_PAD_GAP)) for sh in own_pads):
                            continue                     # no via in a surface pad, its own net's included
                        if not _hole_free(_holes(board), pos, MM(r["drill"])):
                            continue
                        if not clear(end, pos):
                            continue
                        t = P.PCB_TRACK(board)
                        t.SetStart(end)
                        t.SetEnd(pos)
                        t.SetWidth(width)
                        t.SetLayer(P.F_Cu)
                        t.SetNet(net)
                        board.Add(t)
                        via = P.PCB_VIA(board)
                        via.SetPosition(pos)
                        via.SetWidth(MM(r["via"]))
                        via.SetDrill(MM(r["drill"]))
                        via.SetNet(net)
                        board.Add(via)
                        done = True
                        break
                    if done:
                        break
                if done:
                    break
        if not done:
            done = maze(board, spec, net, a, b, track_width(spec, net))
            if done:
                print(f"  repair: {pair['net']} joined by the maze router")
        for radius in (1.2, 2.0) if not done else ():
            # Boxed in by the autorouter's own tracks: lift the ones next to the two ends, route
            # this net, then route every lifted net back. All or nothing: if any of them finds
            # no way, the new copper comes out and everything lifted goes back as it was.
            lifted = _lift_near(board, spec, net, [a, b], MM(radius))
            if not lifted:
                continue
            got = maze(board, spec, net, a, b, track_width(spec, net))
            added = [item for item in got if item is not None]
            ok = bool(got)
            if ok:
                ok, more = _rejoin(board, spec, lifted, MM(r["track"]))
                added += more
            if ok:
                print(f"  repair: {pair['net']} joined after re-routing {sorted({t.GetNetname() for t in lifted})} "
                      f"around it ({radius} mm)")
                done = True
                break
            for item in added:
                _remove(board, item)
            for t in lifted:
                board.Add(t)
        fixed += 1 if done else 0
        if not done:
            print(f"  repair: could not close {pair['net']} at {pair['a']} - {pair['b']}")
    filler = P.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    join_all_fragments(board, spec, filler)       # the new copper can leave a pour fragment with no via
    if prune_dangling(board, spec):
        filler.Fill(board.Zones())
    P.SaveBoard(pcb_path, board)
    print(f"repaired {fixed} of {len(pairs)} open connection(s)")


def ease_vias(board, spec):
    """Step each router via off a surface pad of its own net. Freerouting keeps its vias out of
    a pad (via_at_smd off) but may set one at the pad's very edge, leaving the solder mask no web
    between them. Such a via moves away from the pad, 0.05 mm at a time up to 0.5 mm, with the
    ends of its tracks, to the first spot where it keeps VIA_PAD_GAP from every pad of its net and
    it and its moved tracks clear every other net's copper and every hole. Locked vias (priority
    routes, which the maze router already keeps clear) stay. Returns (moved, left)."""
    r = spec["rules"]
    gap = MM(VIA_PAD_GAP)
    # the widest clearance any net class asks for, so a moved via clears every class
    widest = max([r["clearance"]] + [c.get("clearance", 0) for c in spec.get("netclasses", {}).values()])
    clear = MM(widest + ROUTER_MARGIN)
    edge = MM(r["edge_clearance"] + r["via"] / 2)
    bottom_pours = {z["net"] for z in spec.get("zones", []) if "B.Cu" in z["layers"]}
    drill = MM(r["drill"])
    layers = [P.F_Cu, P.B_Cu] + [getattr(P, f"In{i}_Cu") for i in range(1, spec.get("layers", 2) - 1)]
    smd = [pad for fp in board.GetFootprints() for pad in fp.Pads()
           if pad.GetAttribute() == P.PAD_ATTRIB_SMD and not _exposed_pad(fp, pad)]

    def pad_layer(pad):
        return P.F_Cu if pad.IsOnLayer(P.F_Cu) else P.B_Cu

    moved = left = 0
    for via in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and not t.IsLocked()]:
        code, pos, via_r = via.GetNetCode(), via.GetPosition(), via.GetWidth(P.F_Cu) // 2

        def near(q):
            return [pad for pad in smd if pad.GetNetCode() == code
                    and pad.GetEffectiveShape(pad_layer(pad)).Collide(q, via_r + gap)]

        bad = near(pos)
        if not bad:
            continue
        # tracks that end anywhere on the via, not only at its centre: each end moves with it
        def on_via(e):
            return (e.x - pos.x) ** 2 + (e.y - pos.y) ** 2 <= via_r * via_r
        ends = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetNetCode() == code
                and (on_via(t.GetStart()) or on_via(t.GetEnd()))]
        if any(t.IsLocked() for t in ends):
            left += 1
            continue
        # a same-net track that crosses or grazes the via without ending on it would be cut off
        carried = {e.m_Uuid.AsString() for e in ends}       # by id: each GetTracks() call wraps anew
        if any(t.GetClass() != "PCB_VIA" and t.GetNetCode() == code and t.m_Uuid.AsString() not in carried
               and t.GetEffectiveShape(t.GetLayer()).Collide(pos, via_r) for t in board.GetTracks()):
            left += 1
            continue
        reach = int(MM(0.5) + via_r + clear + max([t.GetLength() for t in ends] + [0]))
        zone_box = P.BOX2I(P.VECTOR2I(pos.x - reach, pos.y - reach), P.VECTOR2I(2 * reach, 2 * reach))
        others = []                               # (shape, layer) of other nets' copper nearby
        for t in board.GetTracks():
            if t.GetNetCode() != code and t.GetBoundingBox().Intersects(zone_box):
                for layer in (layers if t.GetClass() == "PCB_VIA" else [t.GetLayer()]):
                    others.append((t.GetEffectiveShape(layer), layer))
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() != code and pad.GetBoundingBox().Intersects(zone_box):
                    for layer in layers:
                        if pad.IsOnLayer(layer):
                            others.append((pad.GetEffectiveShape(layer), layer))
        holes = [(c, rad) for c, rad in _holes(board) if c != pos]
        c = bad[0].GetPosition()
        ax, ay = pos.x - c.x, pos.y - c.y
        norm = max(1.0, (ax * ax + ay * ay) ** 0.5)
        dirs = [(ax / norm, ay / norm)] + [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7071, 0.7071),
                                           (-0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, -0.7071)]
        done = False
        for step in range(1, 11):
            for ux, uy in dirs:
                q = P.VECTOR2I(int(pos.x + ux * step * MM(0.05)), int(pos.y + uy * step * MM(0.05)))
                if near(q) or not _inside(spec, q, edge) or not _hole_free(holes, q, drill):
                    continue
                if via.GetNetname() not in bottom_pours and _in_bottom_keepout(spec, q, via_r):
                    continue
                if any(sh.Collide(q, via_r + clear) for sh, _ in others):
                    continue
                dx, dy = q.x - pos.x, q.y - pos.y
                ok = True
                for t in ends:
                    near_end = t.GetStart() if on_via(t.GetStart()) else t.GetEnd()
                    far = t.GetEnd() if on_via(t.GetStart()) else t.GetStart()
                    new = P.VECTOR2I(near_end.x + dx, near_end.y + dy)
                    n = max(2, int(((new.x - far.x) ** 2 + (new.y - far.y) ** 2) ** 0.5 / MM(0.02)))
                    pts = [P.VECTOR2I(int(far.x + (new.x - far.x) * k / n), int(far.y + (new.y - far.y) * k / n))
                           for k in range(n + 1)]
                    if not all(_inside(spec, pt, MM(r["edge_clearance"]) + t.GetWidth() // 2) for pt in pts) or any(
                            layer == t.GetLayer() and sh.Collide(pt, t.GetWidth() // 2 + clear)
                            for pt in pts for sh, layer in others):
                        ok = False
                        break
                if not ok:
                    continue
                for t in ends:
                    if on_via(t.GetStart()):
                        t.SetStart(P.VECTOR2I(t.GetStart().x + dx, t.GetStart().y + dy))
                    else:
                        t.SetEnd(P.VECTOR2I(t.GetEnd().x + dx, t.GetEnd().y + dy))
                via.SetPosition(q)
                moved += 1
                done = True
                break
            if done:
                break
        if not done:
            left += 1
    return moved, left


def _fanout_item(t, fanout):
    """True when ``t`` is a fan-out via or stub that place() recorded (``spec["fanout_copper"]``: a via
    as [x, y], a stub as [x0, y0, x1, y1], in nm)."""
    if t.GetClass() == "PCB_VIA":
        return (t.GetPosition().x, t.GetPosition().y) in fanout
    a, b = t.GetStart(), t.GetEnd()
    return (a.x, a.y, b.x, b.y) in fanout or (b.x, b.y, a.x, a.y) in fanout


def prune_dangling(board, spec=None):
    """Remove the router's vias and track stubs that lead nowhere (connected on one layer, or an
    end touching nothing), until none are left, and the fan-out's own locked vias and stubs that do.
    Other locked copper (a reference design's, the priority routes) stays."""
    fanout = {tuple(x) for x in (spec or {}).get("fanout_copper", [])}
    removed = 0
    for _ in range(20):
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        dead = [t for t in board.GetTracks() if (not t.IsLocked() or _fanout_item(t, fanout))
                and conn.TestTrackEndpointDangling(t, False)]
        if not dead:
            break
        for t in dead:
            _remove(board, t)          # see _REMOVED: freeing their proxies breaks the bindings
        removed += len(dead)
    return removed


def finish(spec, pcb_path, ses_path):
    board = P.LoadBoard(pcb_path)
    if not P.ImportSpecctraSES(board, ses_path):
        raise SystemExit("Specctra SES import failed")
    # Freerouting necks a track down to enter a tight pad and can go below the board's minimum
    # width (0.09 mm against 0.1 mm, on EoS ESP32 DevKit). Widen such necks to the minimum: the
    # router kept ROUTER_MARGIN of extra clearance, which leaves room, and DRC checks the result.
    floor = MM(spec["rules"]["min_track"])
    necks = [t for t in board.GetTracks()
             if t.GetClass() != "PCB_VIA" and not t.IsLocked() and t.GetWidth() < floor]   # reference copper stays exact
    for t in necks:
        t.SetWidth(floor)
    if necks:
        print(f"widened {len(necks)} track neck(s) to the {spec['rules']['min_track']} mm minimum")
    moved, left = ease_vias(board, spec)
    if moved or left:
        print(f"vias stepped off their own net's pads: {moved} moved, {left} left where they were")
    # Nets already complete before routing (joined by reference copper alone) are not the
    # router's: it sees zone-joined pads as open and would add a second, needless path.
    done = set(spec.get("complete_nets", []))
    extra = [t for t in board.GetTracks() if not t.IsLocked() and t.GetNetname() in done]
    for t in extra:
        _remove(board, t)
    if extra:
        print(f"removed {len(extra)} router item(s) on nets the reference copper already completes")
    nets = {n.GetNetname(): n for n in board.GetNetsByName().values()} if hasattr(board, "GetNetsByName") else {}
    for z in spec.get("zones", []):
        net = board.FindNet(z["net"])
        for layer in z["layers"]:
            zone(board, net, getattr(P, layer.replace(".", "_")), spec["width"], spec["height"])
        print(f"stitching vias on {z['net']}: {stitch(board, net, spec)}")
    filler = P.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    join_all_fragments(board, spec, filler)
    pruned = prune_dangling(board, spec)
    if pruned:
        print(f"removed {pruned} dangling via(s) and track stub(s)")
        filler.Fill(board.Zones())
    P.SaveBoard(pcb_path, board)
    tracks = [t for t in board.GetTracks()]
    vias = [t for t in tracks if t.GetClass() == "PCB_VIA"]
    print(f"routed: {len(tracks) - len(vias)} track segments, {len(vias)} vias -> {pcb_path}")


if __name__ == "__main__":
    mode, spec_path, pcb, other = sys.argv[1:5]
    spec = json.loads(Path(spec_path).read_text())
    {"place": place, "finish": finish, "repair": repair, "ripup": ripup}[mode](spec, pcb, other)
    if mode == "place":
        # the fiducials placed and their copper-free squares, which finish, repair and rip-up honour
        Path(spec_path).write_text(json.dumps(spec, indent=1))
