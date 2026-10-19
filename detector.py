"""Classical computer-vision inspection (OpenCV). Thresholds are at the top so you can tune them."""
import cv2
import numpy as np

OPEN_KERNEL = 25        # protrusions narrower than this (px) are treated as gate stubs / flash
MIN_AREA = 60           # ignore specks smaller than this
GATE_MAX_ASPECT = 2.0   # compact blob -> gate cut; long thin blob -> scrap flash
GATE_MAJOR_AREA = 500   # gate stub bigger than this -> recycle
FP_HP_THRESH = 8        # lens fingerprint sensitivity (lower = more sensitive)
FP_MIN_AREA = 300

COLORS = {"scrap": (0, 0, 255), "gate_cut": (0, 165, 255), "fingerprint": (255, 200, 0)}
ACTIONS = {
    "PASS": "Qualified - release to assembly.",
    "REWORK": "Minor defect - trim gate / clean lens, then re-inspect.",
    "RECYCLE": "Scrap - move to recycle bin (regrind).",
}


def _largest_mask(binary):
    cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(binary)
    if cnts:
        cv2.drawContours(mask, [max(cnts, key=cv2.contourArea)], -1, 255, -1)
    return mask


def _inspect_part(gray):
    g = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = _largest_mask(th)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OPEN_KERNEL, OPEN_KERNEL))
    diff = cv2.subtract(mask, cv2.morphologyEx(mask, cv2.MORPH_OPEN, k))
    diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(diff)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < MIN_AREA:
            continue
        aspect = max(w, h) / max(1, min(w, h))
        kind = "gate_cut" if aspect < GATE_MAX_ASPECT and area <= 900 else "scrap"
        out.append({"type": kind, "box": [int(x), int(y), int(w), int(h)], "area": int(area)})
    return out


def _inspect_lens(gray):
    mask = _largest_mask((gray > 70).astype(np.uint8) * 255)
    mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    hp = gray.astype(np.float32) - cv2.GaussianBlur(gray, (0, 0), 12)
    cand = ((np.abs(hp) > FP_HP_THRESH) & (mask > 0)).astype(np.uint8) * 255
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(cand)
    return [{"type": "fingerprint", "box": [int(s[0]), int(s[1]), int(s[2]), int(s[3])], "area": int(s[4])}
            for s in stats[1:] if s[4] >= FP_MIN_AREA]


def decide(dets):
    kinds = {d["type"] for d in dets}
    if "scrap" in kinds or any(d["type"] == "gate_cut" and d["area"] > GATE_MAJOR_AREA for d in dets):
        return "RECYCLE"
    if kinds:
        return "REWORK"
    return "PASS"


def inspect(img, part_type="part"):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dets = _inspect_lens(gray) if part_type == "lens" else _inspect_part(gray)
    decision = decide(dets)
    ann = img.copy()
    for d in dets:
        x, y, w, h = d["box"]
        c = COLORS[d["type"]]
        cv2.rectangle(ann, (x - 4, y - 4), (x + w + 4, y + h + 4), c, 2)
        cv2.putText(ann, d["type"], (x, max(14, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)
    return {"defects": dets, "decision": decision, "action": ACTIONS[decision], "annotated": ann}
