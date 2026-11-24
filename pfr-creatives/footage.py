# -*- coding: utf-8 -*-
"""Өз видеоларыңыздан таргет креатив жасау: беттерді автоматты жабу + 9:16 + мәтін/дауыс/музыка.

1) Беттерді жабу (әр клип 9:16-ға кесіледі, беттер мозаика+блюрмен жабылады):
   python3 footage.py anon --model yunet.onnx --out anon/ clip1.mp4 clip2.mov ...
   → anon/clip1.mp4 ... және anon/clip1_check.jpg (тексеру үшін кадрлар)

2) Креативтер (scripts.py сценарийлері, фон ретінде жабылған клиптер):
   python3 footage.py compose --voice kk_KZ-issai-high.onnx --font Montserrat.ttf --out videos_own/ anon/*.mp4 [--ids 01_negizgi,02_trevoga]
"""
import argparse, os, sys, glob, math, subprocess, tempfile
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30

# ------------------------------------------------------------------ face anonymisation

def probe(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, n, w, h


def frames(path):
    """Decode via ffmpeg (handles rotation metadata from phones), yields BGR frames at 30 fps."""
    # let ffmpeg autorotate; read real output size from a 1-frame probe
    one = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True).stdout
    if not one: return
    im = cv2.imdecode(np.frombuffer(one, np.uint8), cv2.IMREAD_COLOR)
    h, w = im.shape[:2]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                            stdout=subprocess.PIPE)
    size = w * h * 3
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size: break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    finally:
        proc.stdout.close(); proc.kill(); proc.wait()


class Detector:
    def __init__(self, model, thr=0.45):
        self.det = cv2.FaceDetectorYN.create(model, "", (320, 320), thr, 0.3, 50)

    def __call__(self, img):
        h, w = img.shape[:2]
        s = 720 / max(h, w)
        small = cv2.resize(img, (int(w * s), int(h * s)))
        self.det.setInputSize((small.shape[1], small.shape[0]))
        _, faces = self.det.detect(small)
        out = []
        if faces is not None:
            for f in faces:
                x, y, bw, bh = f[:4] / s
                out.append((x, y, bw, bh))
        # mirrored pass catches some profiles
        return out


def cover_box(x, y, bw, bh):
    cx, cy = x + bw / 2, y + bh / 2 - bh * 0.05
    return cx, cy, bw * 1.7 / 2, bh * 1.85 / 2   # ellipse centre + radii (hair, chin, ears)


def anonymize_frame(img, ellipses):
    """Each face: ~7 mosaic blocks across + heavy blur, feathered ellipse."""
    if not ellipses: return img
    out = img.copy()
    h, w = img.shape[:2]
    for cx, cy, rx, ry in ellipses:
        x0, x1 = int(max(0, cx - rx * 1.2)), int(min(w, cx + rx * 1.2))
        y0, y1 = int(max(0, cy - ry * 1.2)), int(min(h, cy + ry * 1.2))
        if x1 - x0 < 4 or y1 - y0 < 4: continue
        roi = out[y0:y1, x0:x1]
        rh, rw = roi.shape[:2]
        nb = max(2, int(rw / (2 * rx / 7)))
        mos = cv2.resize(cv2.resize(roi, (nb, max(2, int(nb * rh / rw))), interpolation=cv2.INTER_AREA),
                         (rw, rh), interpolation=cv2.INTER_NEAREST)
        mos = cv2.GaussianBlur(mos, (0, 0), rx / 9)
        m = np.zeros((rh, rw), np.uint8)
        cv2.ellipse(m, (int(cx - x0), int(cy - y0)), (int(rx), int(ry)), 0, 0, 360, 255, -1)
        k = max(3, int(rx * 0.2) | 1)
        m = cv2.GaussianBlur(m, (k, k), 0).astype(np.float32)[..., None] / 255
        out[y0:y1, x0:x1] = (roi * (1 - m) + mos * m).astype(np.uint8)
    return out


def to_vertical(img, cx_frac):
    """Scale to cover 1080x1920 and crop horizontally around cx_frac."""
    h, w = img.shape[:2]
    s = max(W / w, H / h)
    img = cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    nh, nw = img.shape[:2]
    x0 = int(np.clip(cx_frac * nw - W / 2, 0, nw - W))
    y0 = int((nh - H) / 2)
    return img[y0:y0 + H, x0:x0 + W]


def anonymize(path, model, outdir, hold=90):
    det = Detector(model)
    # pass 1: detect on every frame
    dets = [det(f) for f in frames(path)]
    n = len(dets)
    if n == 0: raise SystemExit(f"cannot read {path}")
    sample = next(frames(path))
    sh, sw = sample.shape[:2]
    xs = [x + bw / 2 for d in dets for (x, y, bw, bh) in d]
    cx_frac = float(np.median(xs) / sw) if xs else 0.5
    # temporal fill: every frame is covered with the faces of the nearest detected frame
    # before AND after it (up to `hold` frames away) — so faces hidden by hands/turns stay covered
    hit = [i for i, d in enumerate(dets) if d]
    ell = [[] for _ in range(n)]
    import bisect
    for j in range(n):
        k = bisect.bisect_left(hit, j)
        for i in ([hit[k - 1]] if k > 0 else []) + ([hit[k]] if k < len(hit) else []):
            if abs(i - j) <= hold:
                ell[j] += [cover_box(*b) for b in dets[i]]
    # merge near-duplicate ellipses (keep the bigger one) to save time
    def dedupe(es):
        es = sorted(es, key=lambda e: -e[2])
        keep = []
        for e in es:
            if all(math.hypot(e[0] - k[0], e[1] - k[1]) > k[2] * 0.35 or e[2] > k[2] * 1.3 for k in keep):
                keep.append(e)
        return keep
    base = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir, base + ".mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    checks = []
    covered = 0
    for i, f in enumerate(frames(path)):
        es = dedupe(ell[i]) if i < n else []
        covered += bool(es)
        g = to_vertical(anonymize_frame(f, es), cx_frac)
        ff.stdin.write(np.ascontiguousarray(g).tobytes())
        if i % max(1, n // 8) == 0 and len(checks) < 8:
            checks.append(cv2.resize(g, (270, 480)))
    ff.stdin.close(); ff.wait()
    sheet = np.hstack(checks)
    cv2.imwrite(os.path.join(outdir, base + "_check.jpg"), sheet)
    print(f"{out}: {n} frames, faces covered on {covered} ({100 * covered / n:.0f}%)", flush=True)
    return out


# ------------------------------------------------------------------ footage background for make_creatives.build

class FootageBackground:
    """Plays anonymised clips in sequence (2.5–4.5 s each, crossfades), graded for pain → hope."""

    def __init__(self, clips, seed=0):
        self.clips = []
        for c in clips:
            fr = [cv2.cvtColor(f if f.shape[:2] == (H, W) else to_vertical(f, 0.5), cv2.COLOR_BGR2RGB) for f in frames(c)]
            if fr: self.clips.append(fr)
        rng = np.random.default_rng(seed)
        order = list(range(len(self.clips))); rng.shuffle(order)
        self.seq, t = [], 0.0
        k = 0
        while t < 600:
            ci = order[k % len(order)]
            L = min(4.5, max(2.5, len(self.clips[ci]) / FPS))
            start = rng.integers(0, max(1, len(self.clips[ci]) - int(L * FPS)))
            self.seq.append((t, L, ci, int(start))); t += L; k += 1
        Y, X = np.mgrid[0:H, 0:W]
        d = np.sqrt(((X - W / 2) / (W * 0.65)) ** 2 + ((Y - H * 0.45) / (H * 0.62)) ** 2)
        self.vig = np.clip(1.15 - d ** 1.6, 0.2, 1).astype(np.float32)[..., None]
        self.grain = [(rng.standard_normal((H // 2, W // 2)) * 7).astype(np.float32) for _ in range(6)]

    def _get(self, idx, t):
        st, L, ci, s0 = self.seq[idx]
        fr = self.clips[ci]
        i = s0 + int((t - st) * FPS)
        return fr[min(max(i, 0), len(fr) - 1)].astype(np.float32)

    def frame(self, t, hope, pulse):
        idx = max(i for i, s in enumerate(self.seq) if s[0] <= t)
        a = self._get(idx, t)
        st = self.seq[idx][0]
        if idx > 0 and t - st < 0.4:
            m = (t - st) / 0.4
            a = a * m + self._get(idx - 1, t) * (1 - m)
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        pain = a * 0.45 + lum[..., None] * 0.55
        pain *= np.array([0.95, 0.92, 1.05], np.float32)
        warm = a * 0.85 + lum[..., None] * 0.15
        warm *= np.array([1.08, 1.0, 0.85], np.float32)
        a = pain * (1 - hope) + warm * hope
        a *= (0.72 + 0.1 * hope + 0.08 * pulse) * (0.45 + 0.55 * self.vig)     # dim for text legibility
        g = self.grain[int(t * FPS) % len(self.grain)]
        a += np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("anon"); a1.add_argument("--model", required=True); a1.add_argument("--out", default="anon")
    a1.add_argument("clips", nargs="+")
    a2 = sub.add_parser("compose"); a2.add_argument("--voice", required=True); a2.add_argument("--font", required=True)
    a2.add_argument("--out", default="videos_own"); a2.add_argument("--ids", default="", help="comma-separated, e.g. 01_negizgi,02_trevoga"); a2.add_argument("clips", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.cmd == "anon":
        for c in a.clips: anonymize(c, a.model, a.out)
    else:
        from make_creatives import build
        from scripts import CREATIVES
        for cr in CREATIVES:
            if a.ids and cr["id"] not in a.ids.split(","): continue
            bg = FootageBackground(a.clips, seed=sum(map(ord, cr["id"])))
            with tempfile.TemporaryDirectory() as tmp:
                out, dur = build(cr, a.voice, a.font, a.out, tmp, bg=bg, suffix="_own")
                print(f"{out}  {dur:.1f}s", flush=True)


if __name__ == "__main__":
    main()
