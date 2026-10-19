"""Built-in synthetic dataset: car parts (good / gate cut / scrap flash) and lenses (clean / fingerprint)."""
import random
from pathlib import Path
import cv2
import numpy as np

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def _rrect(img, x, y, w, h, r, c):
    cv2.rectangle(img, (x + r, y), (x + w - r, y + h), c, -1)
    cv2.rectangle(img, (x, y + r), (x + w, y + h - r), c, -1)
    for cx, cy in [(x + r, y + r), (x + w - r, y + r), (x + r, y + h - r), (x + w - r, y + h - r)]:
        cv2.circle(img, (cx, cy), r, c, -1)


def make_part(kind, rng):
    img = np.full((400, 500, 3), 35, np.uint8)
    x, y, w, h, col = 100, 100, 300, 200, (170, 170, 170)
    _rrect(img, x, y, w, h, 24, col)
    for cx in (165, 335):
        cv2.circle(img, (cx, 200), 22, (35, 35, 35), -1)
    if kind in ("gate", "both"):          # leftover gate stub
        s, gx = rng.randint(14, 20), rng.randint(200, 270)
        cv2.rectangle(img, (gx, y - s), (gx + s, y + 3), col, -1)
    if kind in ("scrap", "both"):         # thin flash spurs sticking out of the edge
        t, L = rng.randint(6, 9), rng.randint(30, 40)
        y0 = rng.randint(130, 250)
        cv2.rectangle(img, (x + w - 2, y0), (x + w + L, y0 + t), col, -1)
        x0 = rng.randint(140, 340)
        cv2.rectangle(img, (x0, y + h - 2), (x0 + t, y + h + L), col, -1)
    img = img.astype(np.float32) + np.random.default_rng(rng.randint(0, 9999)).normal(0, 3, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def make_lens(fingerprint, rng):
    yy, xx = np.mgrid[0:400, 0:500]
    r = np.hypot(xx - 250, yy - 200)
    base = np.where(r < 150, 170 - 60 * (r / 150) ** 2, 30).astype(np.float32)
    if fingerprint:
        cx, cy, ang = rng.randint(200, 300), rng.randint(160, 240), rng.randint(0, 30)
        ridge = np.zeros_like(base)
        for k in range(4, 46, 5):
            cv2.ellipse(ridge, (cx, cy), (k, int(k * 1.3)), ang, 0, 360, 30, 2)
        base += cv2.GaussianBlur(ridge, (0, 0), 1.0) * (r < 150)
    base += np.random.default_rng(rng.randint(0, 9999)).normal(0, 1.5, base.shape)
    return cv2.cvtColor(np.clip(base, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)


def ensure_dataset():
    if SAMPLES.exists() and any(SAMPLES.glob("*.png")):
        return
    SAMPLES.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    plan = [("part", "good", 4), ("part", "gate", 4), ("part", "scrap", 4), ("part", "both", 2),
            ("lens", "clean", 4), ("lens", "fingerprint", 4)]
    for ptype, kind, n in plan:
        for i in range(1, n + 1):
            img = make_part(kind, rng) if ptype == "part" else make_lens(kind == "fingerprint", rng)
            cv2.imwrite(str(SAMPLES / f"{ptype}_{kind}_{i:02d}.png"), img)


def list_samples():
    ensure_dataset()
    names = sorted(p.name for p in SAMPLES.glob("*.png"))
    random.Random(1).shuffle(names)      # mixed order looks like a real line
    return names
