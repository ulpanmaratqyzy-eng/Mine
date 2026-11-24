"""Blur every face except the therapist's (tracked from an anchor point). Soft gaussian blur ("сәл мутный")."""
import cv2, json, sys, numpy as np, bisect
clip, out = sys.argv[1], sys.argv[2]
UPLEFT = sys.argv[3] == 'upleft'
ax, ay = (-1, -1) if UPLEFT else (float(sys.argv[3]), float(sys.argv[4]))
strength = float(sys.argv[5]) if len(sys.argv) > 5 else 0.16
res = json.load(open(clip.replace('.mp4', '.faces.json')))
n = len(res)
anchor = None if ax < 0 else np.array([ax, ay])
labels = []   # per frame: list of (x,y,r,is_therapist)
for fr in res:
    lab = []
    best = None
    if UPLEFT:
        big = [i for i, b in enumerate(fr) if b[2] > 90]
        if len(big) >= 2: best = min(big, key=lambda i: fr[i][0] + fr[i][1])
    elif anchor is not None and fr:
        d = [np.hypot(b[0]-anchor[0], b[1]-anchor[1]) / max(b[2], 60) for b in fr]
        k = int(np.argmin(d))
        if d[k] < 0.75: best = k
    for i, b in enumerate(fr):
        lab.append((b[0], b[1], b[2], i == best))
    if best is not None and anchor is not None:
        anchor = 0.6 * anchor + 0.4 * np.array(fr[best][:2])
    labels.append(lab)
# temporal fill for non-therapist faces: nearest detection before/after within 45 frames
hit = [i for i, l in enumerate(labels) if any(not t for *_, t in l)]
def blur_list(j):
    k = bisect.bisect_left(hit, j); out_ = []
    for i in ([hit[k-1]] if k > 0 else []) + ([hit[k]] if k < len(hit) else []):
        if abs(i - j) <= 45: out_ += [(x, y, r) for x, y, r, t in labels[i] if not t]
    return out_
cap = cv2.VideoCapture(clip)
w, h = int(cap.get(3)), int(cap.get(4))
vw = cv2.VideoWriter(out + '.tmp.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
sheet = []
for j in range(n):
    ok, f = cap.read()
    if not ok: break
    o = f.copy()
    for x, y, r in blur_list(j):
        R = r * 0.85
        x0, x1 = int(max(0, x - R*1.4)), int(min(w, x + R*1.4)); y0, y1 = int(max(0, y - R*1.4)), int(min(h, y + R*1.4))
        roi = o[y0:y1, x0:x1]
        if roi.size == 0: continue
        bl = cv2.GaussianBlur(roi, (0, 0), max(2, r * strength))
        m = np.zeros(roi.shape[:2], np.uint8)
        cv2.ellipse(m, (int(x - x0), int(y - y0)), (int(R), int(R * 1.1)), 0, 0, 360, 255, -1)
        m = cv2.GaussianBlur(m, (0, 0), R * 0.18).astype(np.float32)[..., None] / 255
        o[y0:y1, x0:x1] = (roi * (1 - m) + bl * m).astype(np.uint8)
    vw.write(o)
    if j % max(1, n // 6) == 0 and len(sheet) < 6:
        v = o.copy()
        for x, y, r, t in labels[j]:
            if t: cv2.circle(v, (int(x), int(y)), int(r), (0, 255, 0), 5)
        sheet.append(cv2.resize(v, (270, 480)))
vw.release()
import subprocess
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', out + '.tmp.mp4', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', out], check=True)
import os; os.remove(out + '.tmp.mp4')
cv2.imwrite(out.replace('.mp4', '_check.jpg'), np.hstack(sheet))
print(out, 'therapist frames:', sum(any(t for *_, t in l) for l in labels), '/', n)
