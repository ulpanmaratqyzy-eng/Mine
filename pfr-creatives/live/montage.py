# -*- coding: utf-8 -*-
"""Нақты сессия видеолары + сток-видео + Aigul (Edge TTS) дауысы + фон музыкасы → 9:16 креативтер.

python3 montage.py --live DIR --stock DIR --music DIR --fonts DIR --out DIR [--ids 1_dene_bloktary,...]
  live:  IMG_1204.mp4 ... (беттері бұрын бұлыңғыр етілген, 1080x1920)
  stock: <mixkit id>.mp4
  music: m22.mp3 ...
  fonts: Montserrat.ttf, PTM55FT.ttf
"""
import argparse, asyncio, os, sys, math, subprocess, tempfile, wave, json, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from live_scripts import VIDEOS, PHONE

W, H, FPS, SR = 1080, 1920, 30, 44100
VOICE = "kk-KZ-AigulNeural"
GOLD = (242, 181, 68); ROSE = (255, 96, 96); PAPER = (250, 244, 232)


# ------------------------------------------------------------------ voice

def tts(text, path):
    """Aigul neural voice → 44.1 kHz mono wav; returns (samples, word_boundaries[(t0,t1,word)])."""
    import edge_tts
    meta = path + ".json"
    if not (os.path.exists(path) and os.path.exists(meta)):
        async def go():
            c = edge_tts.Communicate(text, VOICE, rate="-6%", pitch="-2Hz", boundary="WordBoundary",
                                     proxy=os.environ.get("HTTPS_PROXY"))
            audio, words = bytearray(), []
            async for ch in c.stream():
                if ch["type"] == "audio": audio += ch["data"]
                elif ch["type"] == "WordBoundary":
                    words.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]))
            return bytes(audio), words
        for attempt in range(4):
            try:
                audio, words = asyncio.run(go()); break
            except Exception as e:
                if attempt == 3: raise
        mp3 = path + ".mp3"
        open(mp3, "wb").write(audio)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-ar", str(SR), "-ac", "1",
                        "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120", path], check=True)
        json.dump(words, open(meta, "w"), ensure_ascii=False)
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a, json.load(open(meta))


def load_audio(path, channels=2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", str(channels), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, channels) / 32768


# ------------------------------------------------------------------ footage

def src_path(shot, a):
    kind, rest = shot.split(":")
    cid = rest.split("@")[0]
    return (os.path.join(a.live, f"IMG_{cid}.mp4") if kind == "L" else os.path.join(a.stock, f"{cid}.mp4")), kind == "L", \
        (float(rest.split("@")[1]) if "@" in rest else None)


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


class Segment:
    """Streams frames of one shot, slightly oversized for a slow Ken-Burns drift."""
    OW, OH = 1188, 2112

    def __init__(self, shot, dur, a, seed):
        self.path, self.live, start = src_path(shot, a)
        avail = duration(self.path)
        base = 0.85 if self.live else 1.0
        speed = base
        if start is None:
            start = 0.3 if self.live else min(avail * 0.15, max(0, avail - dur * base - 0.3))
        if avail - start < dur * speed:
            speed = max(0.45, (avail - start - 0.05) / dur)
            if avail - start < dur * speed:
                start = max(0, avail - dur * speed - 0.05)
        self.speed = speed
        rng = np.random.default_rng(seed)
        self.dir = rng.choice([-1, 1], 2)
        vf = (f"setpts=PTS/{speed:.4f},fps={FPS},scale={self.OW}:{self.OH}:force_original_aspect_ratio=increase,"
              f"crop={self.OW}:{self.OH}")
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur * speed + 0.5:.3f}",
                                      "-i", self.path, "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     stdout=subprocess.PIPE)
        self.dur, self.last = dur, None
        self.size = self.OW * self.OH * 3

    def frame(self, lt):
        buf = self.proc.stdout.read(self.size)
        if len(buf) == self.size:
            self.last = np.frombuffer(buf, np.uint8).reshape(self.OH, self.OW, 3)
        p = min(1, max(0, lt / max(self.dur, 0.1)))
        dx, dy = self.OW - W, self.OH - H
        x0 = int(dx * (0.5 + 0.5 * self.dir[0] * (p - 0.5)))
        y0 = int(dy * (0.5 + 0.5 * self.dir[1] * (p - 0.5)))
        return self.last[y0:y0 + H, x0:x0 + W]

    def close(self):
        try: self.proc.kill()
        except Exception: pass


# ------------------------------------------------------------------ grading / overlays

Y, X = np.mgrid[0:H, 0:W]
VIG = np.clip(1.25 - (((X - W / 2) / (W * 0.7)) ** 2 + ((Y - H * 0.46) / (H * 0.66)) ** 2) ** 0.9, 0.35, 1).astype(np.float32)[..., None]
yy = np.arange(H, dtype=np.float32)
BAND = (1 - 0.62 * np.clip((yy - 950) / 350, 0, 1) * np.clip((1850 - yy) / 250, 0.55, 1)).astype(np.float32)[:, None, None]
LUMW = np.array([0.299, 0.587, 0.114], np.float32)
rng0 = np.random.default_rng(3)
GRAIN = [np.repeat(np.repeat((rng0.standard_normal((H // 2, W // 2)) * 6).astype(np.float32), 2, 0), 2, 1)[..., None] for _ in range(5)]


def grade(img, mood, live, end=False):
    a = img.astype(np.float32)
    lum = (a @ LUMW)[..., None]
    if mood == "pain":
        a = a * (0.75 if live else 0.55) + lum * (0.25 if live else 0.45)
        a *= np.array([0.94, 0.97, 1.06], np.float32)
        dim = 0.88 if live else 0.82
    else:
        a = a * 0.9 + lum * 0.1
        a *= np.array([1.07, 1.0, 0.88], np.float32)
        dim = 0.9 if live else 0.84
    a = (a - 128) * 1.06 + 128
    a *= dim * VIG
    a *= BAND if not end else 0.42
    return a


class Fonts:
    def __init__(self, d): self.d, self.c = d, {}
    def get(self, name, size, var=None):
        k = (name, size, var)
        if k not in self.c:
            f = ImageFont.truetype(os.path.join(self.d, name), size)
            if var: f.set_variation_by_name(var)
            self.c[k] = f
        return self.c[k]
    def heavy(self, s): return self.get("Montserrat.ttf", s, "ExtraBold")
    def black(self, s): return self.get("Montserrat.ttf", s, "Black")
    def bold(self, s): return self.get("Montserrat.ttf", s, "Bold")
    def semi(self, s): return self.get("Montserrat.ttf", s, "SemiBold")
    def mono(self, s): return self.get("PTM55FT.ttf", s)


def tokens(text):
    out, hl = [], False
    for w in text.split():
        if w.startswith("*"): hl = True; w = w[1:]
        end = "*" in w
        out.append((w.replace("*", ""), hl))
        if end: hl = False
    return out


def layout(text, F, size=76, maxw=940):
    while True:
        f = F.heavy(size); sp = f.getlength(" ")
        lines, cur, cw = [], [], 0
        for w, hl in tokens(text):
            wl = f.getlength(w)
            if cur and cw + sp + wl > maxw: lines.append((cur, cw)); cur, cw = [], 0
            cur.append((w, hl, wl)); cw += (sp if len(cur) > 1 else 0) + wl
        if cur: lines.append((cur, cw))
        if len(lines) <= 4 or size <= 56: return f, sp, lines, size
        size -= 6


# ------------------------------------------------------------------ build one video

def build(v, a, tmp):
    F = Fonts(a.fonts)
    # 1) voice + timeline
    t = 0.2
    tl, voice = [], []
    for i, sc in enumerate(v["scenes"]):
        aud, words = tts(sc["say"], os.path.join(a.cache, f"{v['id']}_{i}.wav"))
        vd = len(aud) / SR
        gap = 3.2 if sc.get("kind") == "end" else (0.25 if sc.get("kind") == "rapid" else 0.35)
        lead = 0.25 if sc.get("kind") == "end" else 0.0
        st = t
        voice.append((t + lead, aud))
        sp0 = words[0][0] if words else 0.0
        sp1 = words[-1][1] if words else vd
        tl.append(dict(sc=sc, start=st, end=st + lead + vd + gap, v0=st + lead + sp0, v1=st + lead + sp1, words=words, lead=lead))
        t = st + lead + vd + gap
    dur = t
    tl[0]["start"] = 0.0
    # rapid scenes: split into sub-shots at sentence boundaries
    for e in tl:
        sc = e["sc"]
        if sc.get("kind") != "rapid": continue
        groups = [g.strip() for g in sc["say"].split(".") if g.strip()]
        counts = [len(g.split()) for g in groups]
        starts, k = [], 0
        for c in counts:
            starts.append(e["start"] + e["lead"] + (e["words"][k][0] if k < len(e["words"]) else 0) - 0.08)
            k += c
        starts[0] = e["start"]
        e["subs"] = [(s, starts[j + 1] if j + 1 < len(starts) else e["end"]) for j, s in enumerate(starts)]
    t_hope = next((e["start"] for e in tl if e["sc"]["mood"] == "hope"), dur)

    # 2) audio
    n = int(dur * SR)
    vt = np.zeros(n, np.float32)
    for st, aud in voice:
        s = int(st * SR); vt[s:s + len(aud)] += aud[:n - s]
    vt = vt / (np.abs(vt).max() + 1e-9) * 0.9
    mfile, moff = v["music"]
    mus = load_audio(os.path.join(a.music, mfile))
    s0 = int(moff * SR)
    mus = mus[s0:s0 + n]
    if len(mus) < n: mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    mus = mus / (np.abs(mus).max() + 1e-9)
    k = int(SR * 0.25)
    cs = np.concatenate([[0.0], np.cumsum(np.abs(vt), dtype=np.float64)])
    idx = np.arange(n)
    lo, hi = np.clip(idx - k // 2, 0, n), np.clip(idx + k // 2, 0, n)
    env = ((cs[hi] - cs[lo]) / k).astype(np.float32)   # fast moving average
    env = np.clip(env / (env.max() + 1e-9) * 5, 0, 1)
    gain = 0.42 - 0.24 * env
    fade = np.ones(n, np.float32)
    fi, fo = int(1.2 * SR), int(2.5 * SR)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    mix = mus * (gain * fade)[:, None] + vt[:, None]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    # 3) video
    out = os.path.join(a.out, f"{v['id']}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "9M",
                           "-bufsize", "18M", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out],
                          stdin=subprocess.PIPE)
    seg, seg_key, prev_last, xf_start = None, None, None, -10
    mono = F.mono(30)
    for fi_ in range(int(dur * FPS)):
        tt = fi_ / FPS
        e = [x for x in tl if x["start"] <= tt][-1] if tt >= tl[0]["start"] else tl[0]
        sc = e["sc"]; kind = sc.get("kind", "line")
        # which shot
        if kind == "rapid":
            j = max(i for i, (s, _) in enumerate(e["subs"]) if s <= tt)
            shot, s_start, s_end = sc["shots"][j], e["subs"][j][0], e["subs"][j][1]
        else:
            shot, s_start, s_end = sc["shot"], e["start"], e["end"]
        key = (id(e), shot, s_start)
        if key != seg_key:
            if seg is not None:
                prev_last = cur.copy(); seg.close()
            seg = Segment(shot, s_end - s_start + 0.4, a, fi_)
            seg_key, xf_start = key, tt
        mood = sc["mood"]
        cur = grade(seg.frame(tt - s_start), mood, seg.live, end=(kind == "end"))
        xf = 0.12 if kind == "rapid" else 0.3
        if prev_last is not None and tt - xf_start < xf:
            m = (tt - xf_start) / xf
            cur = cur * m + prev_last * (1 - m)
        if 0 <= tt - t_hope < 0.35:
            cur = cur + 120 * (1 - (tt - t_hope) / 0.35)
        cur = cur + GRAIN[fi_ % 5]
        frame = Image.fromarray(np.clip(cur, 0, 255).astype(np.uint8)).convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        accent = GOLD if mood == "hope" else ROSE

        # top bar
        d.text((70, 170), "PF_R ТЕРАПИЯ", font=mono, fill=PAPER + (190,))
        if seg.live and kind != "end":
            lab = "НАҚТЫ СЕССИЯ"
            lx = W - 70 - mono.getlength(lab)
            if int(tt * 2) % 2 == 0: d.ellipse((lx - 34, 180, lx - 14, 200), fill=(235, 60, 60, 230))
            d.text((lx, 170), lab, font=mono, fill=PAPER + (220,))
        d.line((70, 215, W - 70, 215), fill=PAPER + (60,), width=2)
        # progress
        d.line((70, 215, 70 + (W - 140) * tt / dur, 215), fill=accent + (200,), width=3)

        if kind == "rapid":
            j = max(i for i, (s, _) in enumerate(e["subs"]) if s <= tt)
            word = sc["words"][j]
            age = tt - e["subs"][j][0]
            q = min(1, age / 0.18)
            size = 150
            f = F.black(size)
            while f.getlength(word) > 960 and size > 70:
                size -= 10; f = F.black(size)
            sc_ = 0.9 + 0.1 * q
            fs = F.black(int(size * sc_))
            ww = fs.getlength(word)
            al = int(255 * q)
            d.text(((W - ww) / 2, 860 - size * sc_ / 2), word, font=fs, fill=accent + (al,), stroke_width=4, stroke_fill=(0, 0, 0, al // 2))
        elif kind == "end":
            age = tt - e["start"]
            def fade_in(t0, dd=0.4): return max(0, min(1, (age - t0) / dd))
            al = int(255 * fade_in(0))
            bf = F.black(220)
            d.text(((W - bf.getlength("PF_R")) / 2, 470 - 30 * (1 - fade_in(0))), "PF_R", font=bf, fill=GOLD + (al,),
                   stroke_width=3, stroke_fill=(0, 0, 0, al // 3))
            cap = "Т Е Р А П И Я"; cf = F.bold(56)
            d.text(((W - cf.getlength(cap)) / 2, 730), cap, font=cf, fill=PAPER + (int(255 * fade_in(0.2)),))
            sub = "3 күн  •  Сайлаубай Айгерім"; sf = F.semi(42)
            d.text(((W - sf.getlength(sub)) / 2, 830), sub, font=sf, fill=PAPER + (int(230 * fade_in(0.4)),))
            pa = fade_in(0.7)
            pf = F.heavy(70); pw = pf.getlength(PHONE)
            bx0, bx1 = (W - pw) / 2 - 50, (W + pw) / 2 + 50
            pulse = 1 + 0.025 * math.sin(age * 5)
            cy = 1040
            hh = 70 * pulse
            d.rounded_rectangle((bx0, cy - hh, bx1, cy + hh), radius=int(hh), fill=GOLD + (int(245 * pa),))
            d.text(((W - pw) / 2, cy - 44), PHONE, font=pf, fill=(25, 18, 12, int(255 * pa)))
            t2 = "Тіркелу үшін жазыңыз"; tf = F.bold(50)
            d.text(((W - tf.getlength(t2)) / 2, 1160), t2, font=tf, fill=PAPER + (int(255 * fade_in(1.0)),))
            ax, ay = W / 2, 1270 + 12 * math.sin(age * 6)
            d.polygon([(ax - 34, ay + 40), (ax + 34, ay + 40), (ax, ay)], fill=GOLD + (int(220 * fade_in(1.2)),))
        else:
            f, sp, lines, size = e.setdefault("lay", layout(sc["text"], F))
            nw = sum(len(l[0]) for l in lines)
            lh = size * 1.22
            y = 1330 - len(lines) * lh / 2
            k = 0
            span = max(0.4, (e["v1"] - e["v0"]) * 0.92)
            for words, lw in lines:
                x = (W - lw) / 2
                for w, hl, wl in words:
                    t_on = e["v0"] + k / max(1, nw) * span - 0.05
                    q = max(0, min(1, (tt - t_on) / 0.14))
                    out_q = max(0, min(1, (e["end"] - tt) / 0.18))
                    al = int(255 * q * out_q)
                    if al > 0:
                        col = accent if hl else PAPER
                        d.text((x, y + 18 * (1 - q)), w, font=f, fill=col + (al,), stroke_width=3, stroke_fill=(0, 0, 0, int(al * 0.6)))
                    x += wl + sp; k += 1
                y += lh
        frame = Image.alpha_composite(frame, ov).convert("RGB")
        if tt > dur - 0.5:
            frame = Image.eval(frame, lambda px, k=(dur - tt) / 0.5: int(px * k))
        ff.stdin.write(frame.tobytes())
    seg.close()
    ff.stdin.close(); ff.wait()
    print(out, f"{dur:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("live", "stock", "music", "fonts", "out"): ap.add_argument("--" + k, required=True)
    ap.add_argument("--cache", default=None); ap.add_argument("--ids", default="")
    a = ap.parse_args()
    a.cache = a.cache or os.path.join(a.out, "_tts")
    os.makedirs(a.out, exist_ok=True); os.makedirs(a.cache, exist_ok=True)
    for v in VIDEOS:
        if a.ids and v["id"] not in a.ids.split(","): continue
        with tempfile.TemporaryDirectory() as tmp:
            build(v, a, tmp)


if __name__ == "__main__":
    main()
