"""Checks of tools/eos_boards/pcb_build.py that need KiCad's own Python (pcbnew).

Run by tests/unit/test_eos_boards.py (PcbBuildKiCadTest) with KiCad's bundled interpreter; not
collected by unittest itself. Prints one line per check, "ok <name>" or "FAIL <name>: <reason>",
and exits non-zero when any check fails.
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "eos_boards"))

import pcbnew as P  # noqa: E402

import pcb_build as B  # noqa: E402

SPEC = {"width": 20.0, "height": 20.0, "corner_radius": 0.0, "router_keepouts": [(15.0, 15.0, 18.0, 18.0)],
        "rules": {"via": 0.6, "drill": 0.3, "min_via": 0.5, "min_drill": 0.25, "clearance": 0.15,
                  "edge_clearance": 0.3, "track": 0.2},
        "netclasses": {"Power": {"track": 0.5, "clearance": 0.2}}}


def new_board():
    """A board with nets GND and SIG and three SMD pads: R1.1 (SIG) at (10, 10), R1.2 (GND) at
    (11, 10), each 0.6 x 0.5 mm, and a 0.6 x 0.5 mm GND pad U1.1 at (5, 5)."""
    board = P.BOARD()
    nets = {}
    for name in ("GND", "SIG"):
        nets[name] = P.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    for ref, pads in (("R1", [("1", 10.0, 10.0, "SIG"), ("2", 11.0, 10.0, "GND")]), ("U1", [("1", 5.0, 5.0, "GND")])):
        fp = P.FOOTPRINT(board)
        fp.SetReference(ref)
        board.Add(fp)
        for num, x, y, net in pads:
            pad = P.PAD(fp)
            pad.SetNumber(num)
            pad.SetAttribute(P.PAD_ATTRIB_SMD)
            pad.SetLayerSet(pad.SMDMask())
            pad.SetShape(P.F_Cu, P.PAD_SHAPE_RECTANGLE)
            pad.SetSize(P.F_Cu, P.VECTOR2I(B.MM(0.6), B.MM(0.5)))
            pad.SetPosition(B.v(x, y))
            pad.SetNet(nets[net])
            fp.Add(pad)
    return board, nets


def track(board, net, a, b, layer=P.F_Cu, locked=False):
    t = P.PCB_TRACK(board)
    t.SetStart(B.v(*a))
    t.SetEnd(B.v(*b))
    t.SetWidth(B.MM(0.2))
    t.SetLayer(layer)
    t.SetNet(net)
    t.SetLocked(locked)
    board.Add(t)
    return t


def via(board, net, x, y, locked=False):
    t = P.PCB_VIA(board)
    t.SetPosition(B.v(x, y))
    t.SetWidth(B.MM(0.6))
    t.SetDrill(B.MM(0.3))
    t.SetNet(net)
    t.SetLocked(locked)
    board.Add(t)
    return t


def refused(fn):
    try:
        fn()
    except SystemExit as e:
        return str(e)
    raise AssertionError("expected SystemExit")


def check_pinned_via_lays_a_locked_via_where_asked():
    board, nets = new_board()
    got = B.pinned_via(board, SPEC, nets["GND"], 8.0, 8.0, 0.5, 0.25)
    assert got.IsLocked() and got.GetNetname() == "GND", "not a locked GND via"
    assert (got.GetPosition().x, got.GetPosition().y) == (B.MM(8.0), B.MM(8.0)), "wrong position"
    assert (got.GetWidth(P.F_Cu), got.GetDrillValue()) == (B.MM(0.5), B.MM(0.25)), "wrong size"
    assert sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA") == 1, "not on the board"


def check_pinned_via_refuses_what_breaks_a_rule():
    cases = {
        "below min via": ((8.0, 8.0, 0.45, 0.25), "via rules"),
        "below min drill": ((8.0, 8.0, 0.5, 0.2), "via rules"),
        "drill not inside the via": ((8.0, 8.0, 0.5, 0.5), "via rules"),
        "board edge": ((0.4, 8.0, 0.5, 0.25), "board edge"),
        "router keep-out": ((16.0, 16.0, 0.5, 0.25), "keep-out"),
        # own-net SMD pad R1.2 ends at x = 11.3; a 0.25 mm radius via at 11.6 leaves 0.05 mm < VIA_PAD_GAP
        "own pad within VIA_PAD_GAP": ((11.6, 10.0, 0.5, 0.25), "R1.2"),
        # other-net pad R1.1 ends at x = 9.7; at 9.3 the via edge is 0.15 mm off, below 0.2 + margin
        "other net's pad": ((9.3, 10.0, 0.5, 0.25), "R1.1"),
    }
    for name, (args, reason) in cases.items():
        board, nets = new_board()
        msg = refused(lambda: B.pinned_via(board, SPEC, nets["GND"], *args))
        assert reason in msg, f"{name}: {msg}"
        assert not any(t.GetClass() == "PCB_VIA" for t in board.GetTracks()), f"{name}: a via was left behind"
    board, nets = new_board()
    B.pinned_via(board, SPEC, nets["GND"], 11.7, 10.0, 0.5, 0.25)      # 0.15 mm off its own pad: allowed


def check_pinned_via_keeps_hole_and_track_clearance():
    board, nets = new_board()
    via(board, nets["SIG"], 8.0, 8.4)            # hole edges 0.4 - 0.125 - 0.15 = 0.125 mm apart
    assert "hole" in refused(lambda: B.pinned_via(board, SPEC, nets["GND"], 8.0, 8.0, 0.5, 0.25))
    board, nets = new_board()
    track(board, nets["SIG"], (6.0, 8.5), (9.0, 8.5))  # 0.5 - 0.1 - 0.25 = 0.15 mm, below 0.2 + margin
    assert "SIG copper" in refused(lambda: B.pinned_via(board, SPEC, nets["GND"], 8.0, 8.0, 0.5, 0.25))
    board, nets = new_board()
    track(board, nets["GND"], (6.0, 8.0), (9.0, 8.0))  # its own net's track: no clearance needed
    B.pinned_via(board, SPEC, nets["GND"], 8.0, 8.0, 0.5, 0.25)


def check_route_options_parse_the_pinned_via_and_refuse_the_rest():
    pads = (("U4", "9"), ("R7", "1"))
    assert B.route_options(pads) == (False, None, None)
    assert B.route_options(pads + ("join", 0.15)) == (True, 0.15, None)
    assert B.route_options(pads + ({"via": [19.75, 35.2, 0.5, 0.25]},)) == (False, None, [19.75, 35.2, 0.5, 0.25])
    for bad in ("joins", True, 0, -0.2, {"via": [1, 2, 3]}, {"vias": [1, 2, 0.5, 0.25]}, [0.15]):
        assert refused(lambda: B.route_options(pads + (bad,))), repr(bad)
    assert "together" in refused(lambda: B.route_options(pads + ("join", {"via": [1, 2, 0.5, 0.25]})))


def check_endpoint_layers_by_board_order_unless_via_first():
    """A bottom-layer track ending on a via at (6, 3). Board order (GetTracks(), which lists the
    newest item first) decides unless via_first is set: the default must stay what every board
    without a pinned via was built with."""
    at = B.v(6.0, 3.0)
    for first in ("PCB_TRACK", "PCB_VIA"):
        board, nets = new_board()
        gnd = nets["GND"]
        add = [lambda: via(board, gnd, 6.0, 3.0), lambda: track(board, gnd, (3.0, 3.0), (6.0, 3.0), P.B_Cu)]
        for fn in (add if first == "PCB_TRACK" else add[::-1]):
            fn()
        order = [t.GetClass() for t in board.GetTracks()]
        assert order[0] == first, f"board order {order}"
        expected = [P.B_Cu] if first == "PCB_TRACK" else [P.F_Cu, P.B_Cu]
        assert B._endpoint_layers(board, gnd, at) == expected, f"{first} first: board order decides"
        assert B._endpoint_layers(board, gnd, at, via_first=True) == [P.F_Cu, P.B_Cu], f"{first} first: via_first"
    board, nets = new_board()
    assert B._endpoint_layers(board, nets["GND"], B.v(11.0, 10.0), via_first=True) == [P.F_Cu], "an SMD pad"
    assert B._endpoint_layers(board, nets["GND"], B.v(2.0, 2.0)) == [P.F_Cu], "nothing there"


def check_prune_dangling_counts_from_the_clean_pass():
    board, nets = new_board()
    track(board, nets["GND"], (11.0, 10.0), (5.0, 5.0), locked=True)   # R1.2 to U1.1: connected
    via(board, nets["GND"], 3.0, 15.0)                                  # leads nowhere
    track(board, nets["GND"], (12.0, 15.0), (14.0, 15.0))               # a stub on its own
    counts = []
    removed = B.prune_dangling(board, counts)
    assert removed == 2, f"removed {removed}, expected the via and the stub"
    assert counts == [1, 0], f"counts {counts}, expected one segment and no via"
    assert [t.GetClass() for t in board.GetTracks()] == ["PCB_TRACK"], "the locked track must stay"
    assert B.prune_dangling(board) == 0, "a second pass finds nothing"


def main():
    failed = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("check_")):
        try:
            fn()
            print(f"ok {name}")
        except Exception as e:  # noqa: BLE001 -- report every check, not only the first failure
            failed += 1
            print(f"FAIL {name}: {e!r}\n{traceback.format_exc()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
