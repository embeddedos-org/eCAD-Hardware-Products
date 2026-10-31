"""Find the lines on EoS boards whose ESD part hangs on a stub instead of lying on the line.

Run by tests/unit/test_eos_boards.py (EsdFlowKiCadTest) with KiCad's bundled interpreter; not
collected by unittest itself. A USBLC6-2SC6 or TPD4EUSB30 has two pads per protected line. Only
the copper inside either pad is taken away; a track that runs into a pad keeps the part of it
outside the pad. What is left of the line should fall apart, so the line's ends meet only over
the ESD part. Left joined, the ends meet beside the part and its pads sit on a stub. Prints
"checked <board>" per board and "stub <board> <ref>.<a>/<b>" per such line.
"""

from pathlib import Path

import pcbnew as P

BOARDS = Path(__file__).resolve().parents[2] / "boards" / "eos"
PAIRS = {"USBLC6-2SC6": [("1", "6"), ("3", "4")],
         "TPD4EUSB30": [("1", "10"), ("2", "9"), ("4", "7"), ("5", "6")]}


def _touches(item, pad):
    for layer in (P.F_Cu, P.B_Cu):
        if not pad.IsOnLayer(layer):
            continue
        if item.GetClass() == "PCB_VIA":
            if pad.GetEffectiveShape(layer).Collide(item.GetPosition(), item.GetWidth(layer) // 2):
                return True
        elif item.GetLayer() == layer and pad.GetEffectiveShape(layer).Collide(
                P.SEG(item.GetStart(), item.GetEnd()), item.GetWidth() // 2):
            return True
    return False


def _joined(a, b):
    """Two copper items of one net touch."""
    if a.GetClass() == "PCB_VIA" and b.GetClass() == "PCB_VIA":
        return False
    if b.GetClass() == "PCB_VIA":
        a, b = b, a
    if a.GetClass() == "PCB_VIA":
        return b.GetEffectiveShape(b.GetLayer()).Collide(a.GetPosition(), a.GetWidth(P.F_Cu) // 2)
    if a.GetLayer() != b.GetLayer():
        return False
    return a.GetEffectiveShape(a.GetLayer()).Collide(P.SEG(b.GetStart(), b.GetEnd()), b.GetWidth() // 2)


def _at(start, end, t):
    return P.VECTOR2I(int(round(start.x + (end.x - start.x) * t)),
                      int(round(start.y + (end.y - start.y) * t)))


def _centre_inside(start, end, shape):
    """The share of the segment, as (t0, t1), whose centre lies inside ``shape``."""
    def inside(t):
        return shape.Collide(_at(start, end, t), 0)

    if not shape.Collide(P.SEG(start, end), 0) and not inside(0.0) and not inside(1.0):
        return None
    seed = 0.0 if inside(0.0) else 1.0 if inside(1.0) else _seed(inside, start, end, shape, 0.0, 1.0)
    if seed is None:
        return None
    left = 0.0 if inside(0.0) else _boundary(inside, 0.0, seed, True)
    right = 1.0 if inside(1.0) else _boundary(inside, seed, 1.0, False)
    return None if right <= left else (left, right)


def _boundary(inside, lo, hi, entering):
    for _ in range(50):
        mid = (lo + hi) / 2
        if inside(mid) == entering:
            hi = mid
        else:
            lo = mid
    return hi if entering else lo


def _seed(inside, start, end, shape, lo, hi, depth=0):
    mid = (lo + hi) / 2
    if inside(mid):
        return mid
    if depth > 40:
        return None
    if shape.Collide(P.SEG(_at(start, end, lo), _at(start, end, mid)), 0):
        found = _seed(inside, start, end, shape, lo, mid, depth + 1)
        if found is not None:
            return found
    if shape.Collide(P.SEG(_at(start, end, mid), _at(start, end, hi)), 0):
        return _seed(inside, start, end, shape, mid, hi, depth + 1)
    return None


def _merge(spans):
    out = []
    for a, b in sorted(spans):
        if not out or a > out[-1][1]:
            out.append([a, b])
        else:
            out[-1][1] = max(out[-1][1], b)
    return [(a, b) for a, b in out]


def _outside(spans):
    gaps, cursor = [], 0.0
    for a, b in spans:
        if a > cursor:
            gaps.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < 1.0:
        gaps.append((cursor, 1.0))
    return gaps


def _centre_in_pad(pos, pad):
    for layer in (P.F_Cu, P.B_Cu):
        if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(pos, 0):
            return True
    return False


def _without_pad_copper(board, track, esd):
    """The track with only the copper inside an ESD pad removed. A via whose centre is inside a
    pad is dropped. A track that does not enter a pad is kept whole."""
    if track.GetClass() == "PCB_VIA":
        return [] if any(_centre_in_pad(track.GetPosition(), p) for p in esd) else [track]
    spans = []
    for pad in esd:
        if pad.IsOnLayer(track.GetLayer()):
            span = _centre_inside(track.GetStart(), track.GetEnd(), pad.GetEffectiveShape(track.GetLayer()))
            if span:
                spans.append(span)
    if not spans:
        return [track]
    kept = []
    start, end = track.GetStart(), track.GetEnd()
    for a, b in _outside(_merge(spans)):
        sa, sb = _at(start, end, a), _at(start, end, b)
        if sa == sb:
            continue
        piece = P.PCB_TRACK(board)
        piece.SetStart(sa)
        piece.SetEnd(sb)
        piece.SetWidth(track.GetWidth())
        piece.SetLayer(track.GetLayer())
        piece.SetNet(track.GetNet())
        kept.append(piece)
    return kept


def bypasses(board, fp, a, b):
    """True when the line through fp's pads a and b joins its other pads without them."""
    esd = [fp.FindPadByNumber(a), fp.FindPadByNumber(b)]
    code = esd[0].GetNetCode()
    if code != esd[1].GetNetCode():
        # An unused channel (both pads no-connect) is not a line. A signal split across the two pads is.
        def bare(pad):
            return pad.GetNetCode() <= 0 or pad.GetNetname().startswith("unconnected")
        if bare(esd[0]) and bare(esd[1]):
            return False
        raise SystemExit(f"{fp.GetReference()}.{a} and .{b} are on different nets")
    if any(z.GetNetCode() == code and not z.GetIsRuleArea() for z in board.Zones()):
        raise SystemExit(f"{esd[0].GetNetname()} has a copper zone, which this check does not follow")
    raw = [t for t in board.GetTracks() if t.GetNetCode() == code]
    items = [piece for t in raw for piece in _without_pad_copper(board, t, esd)]
    ends = [p for f in board.GetFootprints() for p in f.Pads()
            if p.GetNetCode() == code and p not in esd]
    group = list(range(len(items) + len(ends)))

    def root(i):
        while group[i] != i:
            group[i] = group[group[i]]
            i = group[i]
        return i

    for i, x in enumerate(items):
        for j in range(i + 1, len(items)):
            if _joined(x, items[j]):
                group[root(i)] = root(j)
        for k, pad in enumerate(ends):
            if _touches(x, pad):
                group[root(i)] = root(len(items) + k)
    return len({root(len(items) + k) for k in range(len(ends))}) < 2


def _mm(mm):
    return int(round(mm * 1_000_000))


def _smd(fp, number, x, y, net):
    pad = P.PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(P.PAD_ATTRIB_SMD)
    pad.SetLayerSet(pad.SMDMask())
    pad.SetShape(P.F_Cu, P.PAD_SHAPE_RECTANGLE)
    pad.SetSize(P.F_Cu, P.VECTOR2I(_mm(0.6), _mm(0.5)))
    pad.SetPosition(P.VECTOR2I(_mm(x), _mm(y)))
    pad.SetNet(net)
    fp.Add(pad)


def _net(board, name):
    net = P.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def _fp(board, ref):
    fp = P.FOOTPRINT(board)
    fp.SetReference(ref)
    board.Add(fp)
    return fp


def _segment(board, net, a, b):
    track = P.PCB_TRACK(board)
    track.SetStart(P.VECTOR2I(_mm(a[0]), _mm(a[1])))
    track.SetEnd(P.VECTOR2I(_mm(b[0]), _mm(b[1])))
    track.SetWidth(_mm(0.2))
    track.SetLayer(P.F_Cu)
    track.SetNet(net)
    board.Add(track)


def check_branch_shaped_stub_is_not_hidden():
    """One track runs from the connector into the ESD pad, and the chip's route branches off it
    before the pad. The part is on a stub. Removing that whole track would also remove the
    connector's path to the branch, and the check would miss the stub."""
    board = P.BOARD()
    net = _net(board, "USB")
    esd = _fp(board, "U2")
    _smd(esd, "1", 10.0, 10.0, net)
    _smd(esd, "6", 10.0, 12.0, net)
    conn = _fp(board, "J1")
    _smd(conn, "1", 2.0, 10.0, net)
    chip = _fp(board, "U1")
    _smd(chip, "1", 6.0, 14.0, net)
    _segment(board, net, (2.0, 10.0), (10.0, 10.0))     # into the pad, past the branch
    _segment(board, net, (6.0, 10.0), (6.0, 14.0))      # the chip, off the track before the pad
    if not bypasses(board, esd, "1", "6"):
        raise SystemExit("branch-shaped stub was hidden")

    through = P.BOARD()
    net = _net(through, "USB")
    esd = _fp(through, "U2")
    _smd(esd, "1", 10.0, 10.0, net)
    _smd(esd, "6", 10.0, 12.0, net)
    _smd(_fp(through, "J1"), "1", 2.0, 10.0, net)
    _smd(_fp(through, "U1"), "1", 10.0, 16.0, net)
    _segment(through, net, (2.0, 10.0), (10.0, 10.0))   # connector to one pad
    _segment(through, net, (10.0, 12.0), (10.0, 16.0))  # the other pad to the chip
    if bypasses(through, esd, "1", "6"):
        raise SystemExit("a line that passes over the part was called a stub")
    print("ok branch-shaped stub")


def main():
    check_branch_shaped_stub_is_not_hidden()
    for pcb in sorted(BOARDS.glob("*/hardware/*.kicad_pcb")):
        board = P.LoadBoard(str(pcb))
        for fp in board.GetFootprints():
            for a, b in PAIRS.get(fp.GetValue(), []):
                if bypasses(board, fp, a, b):
                    print(f"stub {pcb.stem} {fp.GetReference()}.{a}/{b}")
        print(f"checked {pcb.stem}")


if __name__ == "__main__":
    main()
