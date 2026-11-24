# -*- coding: utf-8 -*-
"""PF_R терапия креативтерін 9:16 (1080x1920) MP4 форматында жасайды.

Қажет: ffmpeg, numpy, Pillow, piper-tts, қазақша Piper моделі (kk_KZ-issai-high).
Қолдану:
  python3 make_creatives.py --voice /path/kk_KZ-issai-high.onnx --font /path/Montserrat.ttf --out out [id ...]
"""
import argparse, os, subprocess, sys, wave, math, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts import CREATIVES

W, H, FPS, SR = 1080, 1920, 30, 44100
PAIN_ACCENT = (255, 70, 70)
HOPE_ACCENT = (255, 200, 90)

# ---------------------------------------------------------------- audio utils

def tts(text, speaker, voice, tmpdir, idx):
    raw = os.path.join(tmpdir, f"v{idx}.wav")
    out = os.path.join(tmpdir, f"v{idx}_44.wav")
    subprocess.run([sys.executable, "-m", "piper", "-m", voice, "-s", str(speaker),
                    "--length-scale", "1.12", "--noise-scale", "0.55", "--noise-w-scale", "0.7",
                    "-f", raw], input=text.encode("utf-8"), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ar", str(SR), "-ac", "1",
                    "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                           "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                           "highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80",
                    out], check=True)
    with wave.open(out) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a / (np.abs(a).max() + 1e-9) * 0.9


def fft_convolve(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]


def reverb(x, secs=2.2, mix=0.35, seed=1):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir /= np.sqrt((ir ** 2).sum())
    return x * (1 - mix) + fft_convolve(x, ir) * mix


def saw(f, t, bright=6.0):
    out = np.zeros_like(t)
    k = 1
    while k * f < 2500 and k < 40:
        out += np.sin(2 * np.pi * k * f * t) / k * math.exp(-k / bright)
        k += 1
    return out


def env_ar(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] *= np.linspace(1, 0, r)
    return e


def make_music(dur, t_hope, seed=0):
    """Ауырсыну бөлігі: төмен дрон + жүрек соғысы + диссонанс. Үміт бөлігі: жылы аккорд."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    mix = np.zeros(n)
    ih = int(t_hope * SR)
    pain_env = np.clip((t_hope + 0.6 - t) / 1.2, 0, 1) * np.clip(t / 1.5, 0, 1)
    rise = np.clip(t / max(t_hope, 1), 0, 1)

    # drone (A1 + Bb1 dissonance + E2)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    drone = saw(55, t, 4) * 0.5 + saw(58.27, t, 3) * 0.22 * rise + saw(82.4, t, 3) * 0.25
    mix += drone * lfo * pain_env * 0.55
    # high tense cluster
    hi = (np.sin(2 * np.pi * 880 * t) + np.sin(2 * np.pi * 932.3 * t) + 0.6 * np.sin(2 * np.pi * 1318 * t))
    hi *= (0.5 + 0.5 * np.sin(2 * np.pi * 5.5 * t)) * rise ** 1.5
    mix += hi * pain_env * 0.035

    # heartbeat
    beats = []
    tb, period = 0.8, 1.0
    while tb < t_hope - 0.5:
        beats.append(tb)
        tb += period
        period = max(0.72, period - 0.012)
    for b in beats:
        for off, amp in ((0, 1.0), (0.24, 0.7)):
            s = int((b + off) * SR)
            m = int(0.35 * SR)
            if s + m > n: continue
            tt = np.arange(m) / SR
            f = 48 + 40 * np.exp(-tt * 30)
            thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14)
            mix[s:s + m] += thump * amp * 0.9

    # riser before hope + sub boom on hope
    r0 = max(0, ih - int(2.0 * SR))
    if ih > r0:
        m = ih - r0
        noise = rng.standard_normal(m)
        noise = np.convolve(noise, np.ones(8) / 8, mode="same")
        mix[r0:ih] += noise * np.linspace(0, 1, m) ** 3 * 0.25
    m = min(int(2.5 * SR), n - ih)
    if m > 0:
        tt = np.arange(m) / SR
        f = 40 + 60 * np.exp(-tt * 8)
        mix[ih:ih + m] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2) * 0.9

    # hope pad: D major add9 + soft arpeggio
    if ih < n:
        th = t[ih:] - t_hope
        hn = n - ih
        pad = sum(saw(f, th, 2.5) for f in (146.8, 185.0, 220.0, 329.6)) * 0.18
        pad *= np.clip(th / 1.8, 0, 1) * env_ar(hn, 0, 1.5)
        mix[ih:] += pad
        notes = [293.7, 369.99, 440.0, 587.3, 440.0, 369.99]
        step = 0.42
        k = 0
        while k * step < (dur - t_hope) - 1.0:
            s = ih + int(k * step * SR)
            m = min(int(1.6 * SR), n - s)
            tt = np.arange(m) / SR
            f = notes[k % len(notes)]
            pl = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 3.5)
            mix[s:s + m] += pl * 0.12 * min(1, k / 3 + 0.2)
            k += 1

    mix = reverb(mix, 2.6, 0.4, seed)
    mix *= env_ar(n, 0.05, 1.2)
    return mix / (np.abs(mix).max() + 1e-9), beats


# ---------------------------------------------------------------- text utils

def font(path, size, weight="ExtraBold"):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_name(weight)
    except Exception: pass
    return f


def tokenize(text):
    """'*a b* c' -> [(a,True),(b,True),(c,False)]"""
    out, hl = [], False
    for w in text.split():
        start = w.startswith("*")
        if start: hl = True; w = w[1:]
        end = w.endswith("*") or w.rstrip("?,.!»—").endswith("*")
        if end:
            w = w.replace("*", "")
        out.append((w, hl))
        if end: hl = False
    return out


def layout(tokens, fpath, size, maxw=920):
    f = font(fpath, size)
    sp = f.getlength(" ")
    lines, cur, curw = [], [], 0
    for w, hl in tokens:
        wl = f.getlength(w)
        if cur and curw + sp + wl > maxw:
            lines.append((cur, curw)); cur, curw = [], 0
        cur.append((w, hl, wl)); curw += (sp if len(cur) > 1 else 0) + wl
    if cur: lines.append((cur, curw))
    return f, sp, lines


def fit(text, fpath, size=96, maxlines=5):
    toks = tokenize(text)
    while True:
        f, sp, lines = layout(toks, fpath, size)
        if len(lines) <= maxlines or size <= 56: return f, sp, lines, size
        size -= 6


# ---------------------------------------------------------------- background

class Background:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.lw, self.lh = 108, 192
        yy, xx = np.mgrid[0:self.lh, 0:self.lw]
        self.xx, self.yy = xx / self.lw, yy / self.lh
        self.blobs = [(rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9), rng.uniform(0.15, 0.4),
                       rng.uniform(0.03, 0.09), rng.uniform(0, 6.28), rng.uniform(0.18, 0.35)) for _ in range(6)]
        Y, X = np.mgrid[0:H, 0:W]
        d = np.sqrt(((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H * 0.47) / (H * 0.6)) ** 2)
        self.vig = np.clip(1.15 - d ** 1.6, 0.05, 1).astype(np.float32)[..., None]
        self.grain = [(rng.standard_normal((H // 2, W // 2)) * 9).astype(np.float32) for _ in range(6)]

    def frame(self, t, hope, pulse):
        field = np.zeros((self.lh, self.lw), np.float32)
        for (cx, cy, ax, sp, ph, r) in self.blobs:
            x = cx + ax * math.sin(t * sp * 6.28 + ph)
            y = cy + ax * 0.8 * math.cos(t * sp * 5.1 + ph * 1.3)
            field += np.exp(-((self.xx - x) ** 2 + ((self.yy - y) * 0.56) ** 2) / (2 * r * r))
        field = np.clip(field / 2.2, 0, 1)
        pain_dark, pain_lit = np.array([8, 3, 6]), np.array([120, 14, 28])
        hope_dark, hope_lit = np.array([14, 18, 30]), np.array([200, 130, 60])
        dark = pain_dark * (1 - hope) + hope_dark * hope
        lit = pain_lit * (1 - hope) + hope_lit * hope
        col = dark + field[..., None] * (lit - dark) * (0.85 + 0.35 * pulse)
        img = Image.fromarray(col.astype(np.uint8)).resize((W, H), Image.BILINEAR)
        a = np.asarray(img, np.float32) * (self.vig * (0.9 + 0.15 * pulse))
        g = self.grain[int(t * FPS) % len(self.grain)]
        a += np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- build

def build(cr, voice, fpath, outdir, tmp, bg=None, suffix=""):
    scenes = cr["scenes"]
    timeline = []  # (start, end, scene, extra)
    voice_track = []
    t = 0.25
    idx = 0
    for sc in scenes:
        if sc["kind"] == "list":
            a = tts(sc["say"], cr["speaker"], voice, tmp, idx); idx += 1
            st = t
            voice_track.append((t, a)); t += len(a) / SR + 0.25
            item_times = []
            for label, say in sc["items"]:
                a = tts(say, cr["speaker"], voice, tmp, idx); idx += 1
                item_times.append((t, t + len(a) / SR))
                voice_track.append((t, a)); t += len(a) / SR + 0.18
            t += 0.5
            timeline.append(dict(start=st, end=t, sc=sc, items=item_times))
        else:
            a = tts(sc["say"], cr["speaker"], voice, tmp, idx); idx += 1
            st = t
            voice_track.append((t, a))
            vd = len(a) / SR
            hold = 2.8 if sc["kind"] == "cta" else 0.45
            t += vd + hold
            timeline.append(dict(start=st, end=t, sc=sc, vdur=vd))
    dur = t + 0.2
    t_hope = next(e["start"] for e in timeline if e["sc"]["mood"] == "hope")

    # audio mix
    n = int(dur * SR)
    vt = np.zeros(n)
    for st, a in voice_track:
        s = int(st * SR); vt[s:s + len(a)] += a[:n - s]
    vt = reverb(vt, 0.9, 0.12, 7)
    music, beats = make_music(dur, t_hope, seed=sum(map(ord, cr["id"])))
    venv = np.convolve(np.abs(vt), np.ones(2205) / 2205, mode="same")
    venv = np.clip(venv / (venv.max() + 1e-9) * 6, 0, 1)
    duck = 0.30 - 0.14 * venv
    mixed = vt * 0.95 + music * duck
    mixed = mixed / (np.abs(mixed).max() + 1e-9) * 0.95
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mixed * 32767).astype(np.int16).tobytes())

    # precompute layouts
    for e in timeline:
        sc = e["sc"]
        if sc["kind"] == "list":
            e["hf"] = font(fpath, 92)
            e["if"] = font(fpath, 60, "Bold")
        elif sc["kind"] == "cta":
            e["lay"] = fit(sc["text"], fpath, 70, 4)
        else:
            e["lay"] = fit(sc["text"], fpath, 96 if len(sc["text"]) < 45 else 86)

    bg = bg or Background(sum(map(ord, cr["id"])))
    label_f = font(fpath, 34, "SemiBold")
    big_f = font(fpath, 150, "Black")
    mid_f = font(fpath, 84, "ExtraBold")
    beats_arr = np.array(beats) if beats else np.array([-10.0])

    out = os.path.join(outdir, f"{cr['id']}{suffix}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out],
                          stdin=subprocess.PIPE)
    nframes = int(dur * FPS)
    for fi in range(nframes):
        tt = fi / FPS
        hope = float(np.clip((tt - t_hope + 0.3) / 1.2, 0, 1))
        db = tt - beats_arr
        db = db[db >= 0]
        pulse = float(np.exp(-db.min() * 5)) if len(db) and hope < 1 else 0.0
        img = bg.frame(tt, hope, pulse * (1 - hope))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        accent = PAIN_ACCENT if hope < 0.5 else HOPE_ACCENT

        # top label
        lab = "ПСИХОЛОГ  •  PF_R ТЕРАПИЯ"
        d.text(((W - label_f.getlength(lab)) / 2, 150), lab, font=label_f, fill=(255, 255, 255, 150))

        for e in timeline:
            if not (e["start"] - 0.05 <= tt < e["end"]): continue
            sc = e["sc"]
            age = tt - e["start"]
            out_a = float(np.clip((e["end"] - tt) / 0.2, 0, 1))
            if sc["kind"] == "list":
                hf, itf = e["hf"], e["if"]
                a = int(255 * min(1, age / 0.25) * out_a)
                tx = sc["text"]
                y0 = 470
                d.text(((W - hf.getlength(tx)) / 2, y0 - 10 * (1 - min(1, age / 0.25))), tx, font=hf,
                       fill=(255, 255, 255, a), stroke_width=3, stroke_fill=(0, 0, 0, a // 2))
                y = y0 + 150
                for (label, _), (s_it, e_it) in zip(sc["items"], e["items"]):
                    if tt < s_it - 0.05: break
                    ia = min(1, (tt - s_it + 0.05) / 0.2)
                    al = int(255 * ia * out_a)
                    x = 150 - 30 * (1 - ia)
                    active = s_it <= tt <= e_it + 0.15
                    col = accent if active else (255, 255, 255)
                    d.ellipse((x, y + 22, x + 22, y + 44), fill=accent + (al,))
                    d.text((x + 50, y), label, font=itf, fill=col + (al,), stroke_width=2,
                           stroke_fill=(0, 0, 0, al // 2))
                    y += 92
            elif sc["kind"] == "cta":
                a = min(1, age / 0.35) * out_a
                al = int(255 * a)
                s1, s2 = "PF_R", "ТЕРАПИЯ"
                yb = 560 - 20 * (1 - a)
                d.text(((W - big_f.getlength(s1)) / 2, yb), s1, font=big_f, fill=HOPE_ACCENT + (al,),
                       stroke_width=4, stroke_fill=(0, 0, 0, al // 3))
                d.text(((W - mid_f.getlength(s2)) / 2, yb + 185), s2, font=mid_f, fill=(255, 255, 255, al))
                f, sp, lines, size = e["lay"]
                y = 1000
                for words, lw in lines:
                    x = (W - lw) / 2
                    for w, hl, wl in words:
                        d.text((x, y), w, font=f, fill=(255, 255, 255, al), stroke_width=2,
                               stroke_fill=(0, 0, 0, al // 2))
                        x += wl + sp
                    y += size * 1.25
                # pulsing arrow
                p = 0.5 + 0.5 * math.sin(age * 6)
                cx, cy = W / 2, y + 60 + 15 * p
                d.polygon([(cx - 45, cy), (cx + 45, cy), (cx, cy + 50)], fill=HOPE_ACCENT + (int(al * (0.6 + 0.4 * p)),))
            else:
                f, sp, lines, size = e["lay"]
                words_all = [w for ln in lines for w in ln[0]]
                nw = len(words_all)
                reveal = max(0.3, e["vdur"] * 0.8)
                lh = size * 1.22
                y = H * 0.44 - len(lines) * lh / 2
                k = 0
                for words, lw in lines:
                    x = (W - lw) / 2
                    for w, hl, wl in words:
                        tw = k / max(1, nw) * reveal
                        wa = float(np.clip((age - tw) / 0.14, 0, 1)) * out_a
                        if wa > 0:
                            al = int(255 * wa)
                            col = accent if hl else (255, 255, 255)
                            d.text((x, y + 14 * (1 - wa)), w, font=f, fill=col + (al,), stroke_width=3,
                                   stroke_fill=(0, 0, 0, int(al * 0.55)))
                        x += wl + sp
                        k += 1
                    y += lh
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    return out, dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for cr in CREATIVES:
        if a.ids and cr["id"] not in a.ids: continue
        with tempfile.TemporaryDirectory() as tmp:
            out, dur = build(cr, a.voice, a.font, a.out, tmp)
            print(f"{out}  {dur:.1f}s", flush=True)


if __name__ == "__main__":
    main()
