"""Find the lines on EoS boards whose ESD part hangs on a stub instead of lying on the line.

Run by tests/unit/test_eos_boards.py (EsdFlowKiCadTest) with KiCad's bundled interpreter; not
collected by unittest itself. A USBLC6-2SC6 or TPD4EUSB30 has two pads per protected line. The
line's copper that touches either pad is taken away; what is left of the line should fall apart,
so the line's ends meet only over the ESD part. Left joined, the ends meet beside the part and
its pads sit on a stub. Prints "checked <board>" per board and "stub <board> <ref>.<a>/<b>" per
such line.
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


def bypasses(board, fp, a, b):
    """True when the line through fp's pads a and b joins its other pads without them."""
    esd = [fp.FindPadByNumber(a), fp.FindPadByNumber(b)]
    code = esd[0].GetNetCode()
    if code != esd[1].GetNetCode():
        raise SystemExit(f"{fp.GetReference()}.{a} and .{b} are on different nets")
    if any(z.GetNetCode() == code and not z.GetIsRuleArea() for z in board.Zones()):
        raise SystemExit(f"{esd[0].GetNetname()} has a copper zone, which this check does not follow")
    items = [t for t in board.GetTracks() if t.GetNetCode() == code and not any(_touches(t, p) for p in esd)]
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


def main():
    for pcb in sorted(BOARDS.glob("*/hardware/*.kicad_pcb")):
        board = P.LoadBoard(str(pcb))
        for fp in board.GetFootprints():
            for a, b in PAIRS.get(fp.GetValue(), []):
                if bypasses(board, fp, a, b):
                    print(f"stub {pcb.stem} {fp.GetReference()}.{a}/{b}")
        print(f"checked {pcb.stem}")


if __name__ == "__main__":
    main()
