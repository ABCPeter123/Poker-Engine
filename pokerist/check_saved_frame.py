"""Compare a saved review image with explicitly labelled expected observations."""
import argparse
import json
from pathlib import Path


def field_results(result, expected):
    rows = []
    def add(field, actual, wanted, missing=False):
        rows.append({"field": field, "expected": wanted, "actual": actual,
                     "status": "missing" if missing else "match" if actual == wanted else "missing" if actual is None else "incorrect"})
    for group in ("hole_slots", "board_slots"):
        if group in expected:
            slots = result.get(group)
            for i, wanted in enumerate(expected[group]):
                if not isinstance(slots,list) or i>=len(slots):
                    add(f"{group}[{i}]",None,wanted,missing=True)
                    continue
                slot = slots[i]
                if slot is not None and (not isinstance(slot,dict) or "candidate" not in slot):
                    add(f"{group}[{i}]","invalid-slot",wanted)
                    continue
                actual = slot.get("candidate") if isinstance(slot, dict) else None
                # A visible but unreadable face is not an empty slot.
                if isinstance(slot, dict) and actual is None and wanted is None:
                    actual = "visible-unreadable"
                add(f"{group}[{i}]", actual, wanted)
    for key, wanted in expected.get("amounts", {}).items():
        candidate = (result.get("number_candidates", {}).get(key) or {}).get("candidate") or {}
        add(f"amount.{key}", candidate.get("value"), wanted)
    observation = result.get("table_observation") or {}
    for seat, wanted in expected.get("bets", {}).items():
        candidate = (observation.get("seats", {}).get(seat) or {}).get("bet") or {}
        add(f"bet.{seat}", candidate.get("value"), wanted)
    if "dealer" in expected:
        add("dealer", (observation.get("dealer") or {}).get("candidate"), expected["dealer"])
    if "turn" in expected:
        add("turn", observation.get("turn_candidate"), expected["turn"])
    for seat, wanted in expected.get("statuses", {}).items():
        add(f"status.{seat}", (observation.get("seats", {}).get(seat) or {}).get("status_candidate"), wanted)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("expected", type=Path)
    parser.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--no-ocr", action="store_true")
    args = parser.parse_args()
    from PIL import Image
    from review import normalize, review_image
    from ocr_runtime import resolve_tesseract
    exe = None
    if not args.no_ocr:
        exe, error = resolve_tesseract()
        if error:
            print(error)
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    with Image.open(args.image) as im:
        if args.crop:
            l,t,r,b = args.crop
            if not (0 <= l < r <= im.width and 0 <= t < b <= im.height):
                parser.error("Crop must be inside the saved image.")
            im = im.crop(args.crop)
        result = review_image(normalize(im), exe, source="saved regression image")
    rows = field_results(result, expected)
    print(json.dumps(rows, indent=2))
    counts = {key: sum(row["status"] == key for row in rows) for key in ("match", "missing", "incorrect")}
    print(json.dumps(counts))
    return 0 if rows and counts["match"] == len(rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())
