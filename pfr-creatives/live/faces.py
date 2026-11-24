import cv2, numpy as np, json, sys, os
model = sys.argv[1]; clip = sys.argv[2]; out = sys.argv[3]
det = cv2.FaceDetectorYN.create(model, "", (320, 320), 0.5, 0.3, 50)
cap = cv2.VideoCapture(clip)
res = []
fi = 0
while True:
    ok, f = cap.read()
    if not ok: break
    h, w = f.shape[:2]
    s = 0.5
    sm = cv2.resize(f, (int(w*s), int(h*s)))
    boxes = []
    for rot in (None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE):
        im = sm if rot is None else cv2.rotate(sm, rot)
        ih, iw = im.shape[:2]
        det.setInputSize((iw, ih))
        _, faces = det.detect(im)
        if faces is None: continue
        for fc in faces:
            x, y, bw, bh, sc = fc[0], fc[1], fc[2], fc[3], fc[14]
            cx, cy = x + bw/2, y + bh/2
            # map centre back to un-rotated small image
            if rot == cv2.ROTATE_90_CLOCKWISE:  cx, cy = cy, (sm.shape[0]-1) - cx
            elif rot == cv2.ROTATE_180:         cx, cy = (sm.shape[1]-1) - cx, (sm.shape[0]-1) - cy
            elif rot == cv2.ROTATE_90_COUNTERCLOCKWISE: cx, cy = (sm.shape[1]-1) - cy, cx
            r = max(bw, bh)
            boxes.append([float(cx/s), float(cy/s), float(r/s), float(sc), 0 if rot is None else 1])
    # NMS by centre distance
    boxes.sort(key=lambda b: -b[3]); keep = []
    for b in boxes:
        if all(np.hypot(b[0]-k[0], b[1]-k[1]) > 0.5*max(b[2], k[2]) for k in keep): keep.append(b)
    res.append(keep); fi += 1
json.dump(res, open(out, "w"))
print(clip, fi, "frames", sum(1 for r in res if r), "with faces")
