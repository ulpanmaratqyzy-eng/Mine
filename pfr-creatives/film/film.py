# -*- coding: utf-8 -*-
"""«ЖҮКТЕН ЖЕРГЕ» — PF_R терапия, 9:16 кинетикалық спокен-ворд фильм.
Стиль: awesome-opus5-5-videos / gdgtify-929495 «BUILD THE FLOOR» бейімделген нұсқасы (PROMPT.md).

python3 film.py --voice kk_KZ-issai-high.onnx --fonts DIR --shots DIR --out film.mp4
fonts DIR: Montserrat.ttf, PT_Serif-Web-Bold.ttf, PT_Serif-Web-Italic.ttf, PTM55FT.ttf
shots DIR: A_room.png B_hands.png C_rain.png D_child.png E_back.png F_steppe.png G_calm.png H_seeds.png I_room.png
"""
import argparse, os, sys, math, wave, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from make_creatives import tts, make_music, reverb, SR

W, H, FPS = 1080, 1920, 30
BG = (18, 10, 14); PAPER = (244, 233, 213); RED = (200, 50, 60); GOLD = (242, 181, 68)
SPEAKER = 4
PFR = "Пэ-эф-эр"

LINES = {
    "l1": "Жертва күйінен шыққыңыз келе ме?",
    "l2": "Жан тыныштығын тапқыңыз келе ме?",
    "l3": "Егер сізде",
    "l4": "Өзіңізді негативті эмоциялардан босатқыңыз келе ме?",
    "l5": "Өміріңізді жаңа деңгейге көтергіңіз келе ме?",
    "l6": f"Онда мен сізді {PFR} терапияға шақырамын.",
    "l7": "Жазылу үшін директке плюс деп жазыңыз.",
}
ITEMS = [("ҚОРҚЫНЫШ", "Қорқыныш."), ("ТРЕВОГА", "Тревога."), ("КІНӘ", "Кінә."), ("ОБИДА", "Обида."),
         ("ЫЗА", "Ыза."), ("СЕНІМСІЗДІК", "Сенімсіздік."), ("ТРАВМА", "Травма."),
         ("БЛОК", "Денедегі блок болса.")]
# экрандағы мәтін (* = ерекшелеу)
SHOW = {
    "l1": "күйінен шыққыңыз келе ме?",
    "l2": "Жан *тыныштығын* тапқыңыз келе ме?",
    "l4": "Өзіңізді негативті эмоциялардан *босатқыңыз* келе ме?",
    "l5": "Өміріңізді *жаңа деңгейге* көтергіңіз келе ме?",
    "l6": "Онда мен сізді *PF_R терапияға* шақырамын",
}


def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_io(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def ease_back(x):
    x = min(max(x, 0), 1); c = 1.6
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


class Fonts:
    def __init__(self, d):
        self.d = d
        self.cache = {}

    def get(self, name, size, var=None):
        k = (name, size, var)
        if k not in self.cache:
            f = ImageFont.truetype(os.path.join(self.d, name), size)
            if var:
                f.set_variation_by_name(var)
            self.cache[k] = f
        return self.cache[k]

    def serif(self, s): return self.get("PT_Serif-Web-Bold.ttf", s)
    def italic(self, s): return self.get("PT_Serif-Web-Italic.ttf", s)
    def heavy(self, s): return self.get("Montserrat.ttf", s, "Black")
    def bold(self, s): return self.get("Montserrat.ttf", s, "Bold")
    def mono(self, s): return self.get("PTM55FT.ttf", s)


def tokens(text):
    out, hl = [], False
    for w in text.split():
        if w.startswith("*"): hl = True; w = w[1:]
        end = "*" in w
        w = w.replace("*", "")
        out.append((w, hl))
        if end: hl = False
    return out


def wrap(text, F, size, maxw=900):
    toks = tokens(text)
    lines, cur, cw = [], [], 0
    for w, hl in toks:
        f = F.italic(size) if hl else F.serif(size)
        wl = f.getlength(w); sp = F.serif(size).getlength(" ")
        if cur and cw + sp + wl > maxw:
            lines.append((cur, cw)); cur, cw = [], 0
        cur.append((w, hl, wl, f)); cw += (sp if len(cur) > 1 else 0) + wl
    if cur: lines.append((cur, cw))
    return lines


def draw_sentence(d, F, text, size, cy, age, vdur, alpha=1.0, hl_col=GOLD, tremble=0.0, t=0.0):
    lines = wrap(text, F, size)
    lh = size * 1.28
    y = cy - len(lines) * lh / 2
    n = sum(len(l[0]) for l in lines)
    reveal = max(0.3, vdur * 0.8)
    sp = F.serif(size).getlength(" ")
    k = 0
    for words, lw in lines:
        x = (W - lw) / 2
        for w, hl, wl, f in words:
            wa = min(1, max(0, (age - k / max(1, n) * reveal) / 0.18)) * alpha
            if wa > 0:
                jx = tremble * math.sin(t * 31 + k * 1.7)
                jy = tremble * math.cos(t * 27 + k * 2.3) + 16 * (1 - wa)
                a = int(255 * wa)
                col = hl_col if hl else PAPER
                d.text((x + jx, y + jy), w, font=f, fill=col + (a,), stroke_width=2, stroke_fill=(0, 0, 0, int(a * .5)))
            x += wl + sp
            k += 1
        y += lh
    return y


# ------------------------------------------------------------------ shots

def load_shot(path, warm):
    im = Image.open(path).convert("RGB").resize((1215, 2160), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(2, 60, 2))
    a = np.asarray(im, np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114])
    if warm:
        a = a * 0.75 + lum[..., None] * 0.25
        a *= np.array([1.08, 0.98, 0.82])
    else:
        a = a * 0.45 + lum[..., None] * 0.55
        a *= np.array([0.92, 0.95, 1.10])
        a = a ** 1.15
    return np.clip(a, 0, 1)


class Shots:
    def __init__(self, d):
        warm = {"F_steppe", "G_calm", "H_seeds", "I_room"}
        self.im = {}
        for f in os.listdir(d):
            k = os.path.splitext(f)[0]
            if f.endswith(".png"):
                self.im[k] = load_shot(os.path.join(d, f), k in warm)

    def frame(self, key, local_t, seed):
        a = self.im[key]
        z = 1.0 + 0.06 * local_t / 6  # slow push-in
        z = min(z, 1.12)
        cw, ch = int(1215 / z), int(2160 / z)
        dx = (1215 - cw) * (0.5 + 0.35 * math.sin(seed + local_t * 0.15))
        dy = (2160 - ch) * (0.5 + 0.35 * math.cos(seed * 1.3 + local_t * 0.12))
        x0, y0 = int(dx), int(dy)
        crop = a[y0:y0 + ch, x0:x0 + cw]
        img = Image.fromarray((crop * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        return np.asarray(img, np.float32)


# ------------------------------------------------------------------ main build

def build(args):
    F = Fonts(args.fonts)
    tmp = tempfile.mkdtemp()
    clips = {}
    idx = 0
    for k, s in LINES.items():
        clips[k] = tts(s, SPEAKER, args.voice, tmp, idx); idx += 1
    item_clips = []
    for _, s in ITEMS:
        item_clips.append(tts(s, SPEAKER, args.voice, tmp, idx)); idx += 1
    L = lambda a: len(a) / SR

    # timeline
    T = {}
    track = []
    t = 0.4
    def put(key, a, gap):
        nonlocal t
        T[key] = (t, t + L(a)); track.append((t, a)); t += L(a) + gap
    put("l1", clips["l1"], 0.7)
    put("l2", clips["l2"], 0.6)
    put("l3", clips["l3"], 0.25)
    T["items"] = []
    for a in item_clips:
        T["items"].append((t, t + L(a))); track.append((t, a)); t += L(a) + 0.32
    t += 0.4
    put("l4", clips["l4"], 0.5)
    s4, e4 = T["l4"]
    t_rel = s4 + (e4 - s4) * 0.62          # «босат…» сәті
    put("l5", clips["l5"], 0.9)
    put("l6", clips["l6"], 0.6)
    put("l7", clips["l7"], 3.0)
    dur = t
    print("duration", round(dur, 2), "release", round(t_rel, 2))

    # ---------------- audio
    n = int(dur * SR)
    vt = np.zeros(n)
    for st, a in track:
        s = int(st * SR); vt[s:s + len(a)] += a[:n - s]
    vt = reverb(vt, 1.0, 0.13, 7)
    music, beats = make_music(dur, t_rel, seed=42)
    # word-landing thuds
    for (st, _) in T["items"]:
        s = int((st + 0.05) * SR); m = int(0.5 * SR)
        if s + m < n:
            tt = np.arange(m) / SR
            fq = 60 + 80 * np.exp(-tt * 25)
            music[s:s + m] += np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-tt * 9) * 0.55
    music /= np.abs(music).max()
    venv = np.convolve(np.abs(vt), np.ones(2205) / 2205, mode="same")
    venv = np.clip(venv / (venv.max() + 1e-9) * 6, 0, 1)
    mixed = vt * 0.95 + music * (0.32 - 0.15 * venv)
    mixed = mixed / np.abs(mixed).max() * 0.95
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mixed * 32767).astype(np.int16).tobytes())

    # ---------------- shot schedule  (start, key)
    s1 = T["l1"][0]; s2, e2 = T["l2"]; s3 = T["l3"][0]; i0 = T["items"][0][0]; i4 = T["items"][4][0]
    s5, e5 = T["l5"]; s6 = T["l6"][0]
    sched = [(0, "A_room"), (s2 - 0.3, "B_hands"), ((s2 + e2) / 2 + 0.3, "C_rain"), (s3 - 0.2, "D_child"),
             (i4, "E_back"), (t_rel, "H_seeds"), (s5 - 0.2, "F_steppe"), ((s5 + e5) / 2 + 0.4, "G_calm"),
             (s6 - 0.3, "I_room")]
    shots = Shots(args.shots)
    XF = 0.7

    def shot_at(tt):
        cur = 0
        for i, (st, k) in enumerate(sched):
            if tt >= st: cur = i
        st, k = sched[cur]
        img = shots.frame(k, tt - st, cur)
        if cur > 0 and tt - st < XF:
            pst, pk = sched[cur - 1]
            prev = shots.frame(pk, tt - pst, cur - 1)
            m = ease_io((tt - st) / XF)
            if k == "H_seeds":  # release: flash
                img = img * m + prev * (1 - m) + 255 * 0.35 * math.sin(math.pi * m)
            else:
                img = img * m + prev * (1 - m)
        return img, k

    # ---------------- static assets
    rng = np.random.default_rng(5)
    Y, X = np.mgrid[0:H, 0:W]
    vig = np.clip(1.2 - (((X - W / 2) / (W * .6)) ** 2 + ((Y - H * .48) / (H * .62)) ** 2) ** .8, .15, 1).astype(np.float32)[..., None]
    grain = [(rng.standard_normal((H // 2, W // 2)) * 10).astype(np.float32) for _ in range(6)]
    grain = [np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None] for g in grain]
    dust = rng.uniform(0, 1, (70, 4))  # x, y, speed, size
    rain = rng.uniform(0, 1, (160, 3))
    bg_arr = np.array(BG, np.float32)

    # stack layout for list words
    ST_F = F.heavy(74)
    cable_x0, cable_x1, cable_y0 = 110, 970, 1300
    offsets = [-34, 28, -18, 40, -40, 12, -24, 30]

    def cable_y(x, sag):
        u = (x - (cable_x0 + cable_x1) / 2) / ((cable_x1 - cable_x0) / 2)
        return cable_y0 + sag * (1 - u * u)

    # particles for release, sampled from the full stack
    stack_mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(stack_mask)
    full_sag = 8 * 14
    for i, (word, _) in enumerate(ITEMS):
        wl = ST_F.getlength(word)
        x = (W - wl) / 2 + offsets[i]
        y = cable_y(W / 2, full_sag) - (i + 1) * 80
        md.text((x, y), word, font=ST_F, fill=255)
    ys, xs = np.nonzero(np.asarray(stack_mask)[::6, ::6] > 128)
    P = np.stack([xs * 6.0, ys * 6.0], 1)
    P = P[rng.choice(len(P), min(1400, len(P)), replace=False)]
    Pv = np.stack([rng.normal(0, 60, len(P)), rng.uniform(-420, -120, len(P))], 1)
    Pph = rng.uniform(0, 6.28, len(P))

    out = args.out
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                           "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                           "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
    beats_arr = np.array(beats or [-10.0])
    sections = [(0, "I. ЖҮК"), (s2 - .3, "II. ДІРІЛ"), (s3 - .2, "III. САЛМАҚ"), (s4, "IV. БОСАУ"),
                (s5 - .2, "V. ДЕҢГЕЙ"), (s6 - .3, "VI. ТІРЕК")]

    for fi in range(int(dur * FPS)):
        tt = fi / FPS
        hope = ease_io((tt - t_rel) / 1.5)
        db = tt - beats_arr; db = db[db >= 0]
        pulse = float(np.exp(-db.min() * 6)) * (1 - hope) if len(db) else 0
        img, key = shot_at(tt)
        dim = 0.42 + 0.22 * hope + 0.08 * pulse
        a = img * dim * vig + bg_arr * (1 - dim) * 0.35
        # flash at release
        if 0 <= tt - t_rel < 0.5:
            a += 90 * (1 - (tt - t_rel) / 0.5)
        a += grain[fi % 6]
        a = np.clip(a, 0, 255).astype(np.uint8)
        base = Image.fromarray(a).convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # particles: dust (always), rain (C_rain)
        for x, y, sp, sz in dust:
            px = (x * W + 20 * math.sin(tt * .4 + y * 9)) % W
            py = (y * H - tt * (15 + 30 * sp)) % H
            r = 1 + 2.5 * sz
            col = GOLD if hope > .5 else PAPER
            d.ellipse((px - r, py - r, px + r, py + r), fill=col + (int(40 + 60 * sz),))
        if key == "C_rain":
            for x, y, sp in rain:
                px = x * W; py = (y * H + tt * (900 + 700 * sp)) % H
                d.line((px, py, px - 3, py + 40 + 30 * sp), fill=(200, 215, 240, 70), width=2)

        # section mark (mono)
        sec = [s for st, s in sections if tt >= st][-1]
        mf = F.mono(30)
        d.text((80, 240), f"{tt:05.2f}", font=mf, fill=PAPER + (130,))
        d.text((W - 80 - mf.getlength(sec), 240), sec, font=mf, fill=(GOLD if hope > .5 else RED) + (200,))
        d.line((80, 285, W - 80, 285), fill=PAPER + (50,), width=1)

        # ---- I. ЖЕРТВА slab over a compressing opening
        a1, b1 = T["l1"]
        if tt < s2 - 0.1:
            age = tt - a1
            fade = min(1, (s2 - 0.1 - tt) / 0.3)
            p = ease_io(tt / (b1 + 0.6))
            hf = F.heavy(200)
            word = "ЖЕРТВА"
            slab_y = 380 + 300 * p
            al = int(255 * min(1, tt / 0.4) * fade)
            d.text(((W - hf.getlength(word)) / 2, slab_y), word, font=hf, fill=RED + (al,))
            top = slab_y + 220
            d.line((90, top, W - 90, top), fill=PAPER + (int(al * .8),), width=4)
            bottom = 1240
            d.line((90, bottom, W - 90, bottom), fill=PAPER + (int(al * .8),), width=4)
            draw_sentence(d, F, SHOW["l1"], 66, (top + bottom) / 2, age, b1 - a1, fade)

        # ---- II. trembling line
        a2, b2 = T["l2"]
        if a2 - 0.1 <= tt < s3 - 0.1:
            fade = min(1, (s3 - 0.1 - tt) / 0.3)
            draw_sentence(d, F, SHOW["l2"], 84, 900, tt - a2, b2 - a2, fade, hl_col=RED, tremble=3.5, t=tt)

        # ---- III. weights on the cable
        a3, b3 = T["l3"]
        if a3 - 0.1 <= tt < t_rel + 0.05:
            landed = 0.0
            shake = 0.0
            for i, (st, _) in enumerate(T["items"]):
                if tt >= st:
                    q = min(1, (tt - st) / 0.38)
                    landed += ease_out(q)
                    if q >= 1:
                        dt = tt - st - 0.38
                        shake += 9 * math.exp(-dt * 7) * math.sin(dt * 40)
            sag = 14 * landed + shake
            hdr_a = min(1, (tt - a3) / 0.3)
            if tt < s4:
                hi = F.italic(76)
                tx = "Егер сізде…"
                d.text(((W - hi.getlength(tx)) / 2, 420), tx, font=hi, fill=PAPER + (int(255 * hdr_a),))
            # cable
            pts = [(x, cable_y(x, sag)) for x in range(cable_x0, cable_x1 + 1, 20)]
            d.line(pts, fill=PAPER + (230,), width=4)
            for x in (cable_x0, cable_x1):
                d.line((x, cable_y0 - 30, x, cable_y0 + 30), fill=PAPER + (230,), width=4)
            # words
            for i, ((word, _), (st, en)) in enumerate(zip(ITEMS, T["items"])):
                if tt < st: break
                q = ease_back(min(1, (tt - st) / 0.38))
                wl = ST_F.getlength(word)
                x = (W - wl) / 2 + offsets[i]
                rest = cable_y(W / 2, sag) - (i + 1) * 80
                y = -120 + (rest + 120) * q
                col = RED if st <= tt <= en + 0.2 else PAPER
                d.text((x, y), word, font=ST_F, fill=col + (255,), stroke_width=2, stroke_fill=(0, 0, 0, 140))

        # ---- IV. sentence + release particles
        a4, b4 = T["l4"]
        if a4 - 0.1 <= tt < s5 - 0.1:
            fade = min(1, (s5 - 0.1 - tt) / 0.3)
            draw_sentence(d, F, SHOW["l4"], 72, 520, tt - a4, b4 - a4, fade, hl_col=GOLD)
        if t_rel <= tt < t_rel + 3.0:
            dt = tt - t_rel
            pp = P + Pv * dt + np.stack([25 * np.sin(Pph + dt * 3), np.zeros(len(P))], 1)
            al = int(255 * max(0, 1 - dt / 3.0))
            for (px, py), ph in zip(pp, Pph):
                r = 2 + 1.5 * math.sin(ph + dt * 5)
                d.ellipse((px - r, py - r, px + r, py + r), fill=GOLD + (al,))
        # cable after release: damped wobble → straight → rises (platform)
        if t_rel <= tt:
            dt = tt - t_rel
            sag = 112 * math.exp(-dt * 3.2) * math.cos(dt * 9)
            rise = ease_io((tt - s5) / max(.5, (e5 - s5))) if tt >= s5 else 0
            y0 = cable_y0 - 150 * rise
            thick = int(4 + 6 * rise)
            mixc = tuple(int(PAPER[c] + (GOLD[c] - PAPER[c]) * min(1, dt / 1.5)) for c in range(3))
            pts = [(x, y0 + sag * (1 - ((x - 540) / 430) ** 2)) for x in range(cable_x0, cable_x1 + 1, 20)]
            d.line(pts, fill=mixc + (240,), width=thick)
            for x in (cable_x0, cable_x1):
                d.line((x, y0 - 30, x, y0 + 30), fill=mixc + (240,), width=4)
            platform_y = y0

        # ---- V. new level
        if s5 - 0.1 <= tt < s6 - 0.1:
            fade = min(1, (s6 - 0.1 - tt) / 0.3)
            draw_sentence(d, F, SHOW["l5"], 84, 700, tt - s5, e5 - s5, fade, hl_col=GOLD)

        # ---- VI. PF_R stands on the platform + CTA
        a6, b6 = T["l6"]
        if tt >= a6 - 0.1:
            age = tt - a6
            draw_sentence(d, F, SHOW["l6"], 76, 600, age, (b6 - a6) * 0.5, 1.0)
            bf = F.heavy(250)
            word = "PF_R"
            q = ease_back(min(1, max(0, (age - (b6 - a6) * 0.35) / 0.5)))
            if q > 0:
                bw = bf.getlength(word)
                bb = bf.getbbox(word)
                ytop = platform_y - bb[3] - 6
                y = -300 + (ytop + 300) * q
                d.text(((W - bw) / 2, y), word, font=bf, fill=GOLD + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 120))
                tf = F.bold(54)
                cap = "Т Е Р А П И Я"
                ca = int(255 * min(1, max(0, (age - (b6 - a6) * 0.6) / 0.4)))
                d.text(((W - tf.getlength(cap)) / 2, platform_y + 34), cap, font=tf, fill=PAPER + (ca,))
        a7, b7 = T["l7"]
        if tt >= a7 - 0.1:
            age = tt - a7
            al = int(255 * min(1, age / 0.4))
            cf = F.bold(50)
            for j, ln in enumerate(["Жазылу үшін директке", "«+» деп жазыңыз"]):
                d.text(((W - cf.getlength(ln)) / 2, 1290 + j * 66), ln, font=cf, fill=PAPER + (al,),
                       stroke_width=2, stroke_fill=(0, 0, 0, al // 2))
            pz = 0.5 + 0.5 * math.sin(age * 6)
            cx, cy = W / 2, 1450 + 14 * pz
            d.polygon([(cx - 40, cy), (cx + 40, cy), (cx, cy + 44)], fill=GOLD + (int(al * (.6 + .4 * pz)),))
        # fade to black at the very end
        frame = Image.alpha_composite(base, ov).convert("RGB")
        if tt > dur - 0.6:
            frame = ImageEnhance.Brightness(frame).enhance(max(0, (dur - tt) / 0.6))
        ff.stdin.write(frame.tobytes())
    ff.stdin.close(); ff.wait()
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True); ap.add_argument("--fonts", required=True)
    ap.add_argument("--shots", required=True); ap.add_argument("--out", default="film.mp4")
    build(ap.parse_args())
