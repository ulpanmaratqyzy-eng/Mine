"""Synthesised 120 BPM soundtrack for one creative (no samples, all code).

Usage: python3 audio.py out.wav '{"dur":15,"cta":12,"hits":[0.5,3]}'
Kick on every beat, clap on 2/4, 8th hats, sub-bass on Am-F-C-G,
soft pad, a riser into the CTA and an impact + whoosh on every hit.
"""
import json, sys, wave
import numpy as np

SR = 44100
BEAT = 0.5


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


def place(buf, sig, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def main(path, meta):
    dur, cta, hits = meta["dur"], meta["cta"], meta["hits"]
    n = int(dur * SR)
    mix = np.zeros(n)
    rng = np.random.default_rng(42)

    # kick
    kn = int(0.35 * SR)
    kt = np.arange(kn) / SR
    freq = 45 + 95 * np.exp(-kt * 28)
    kick = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env(kn, 0.001, 0.12)
    # clap
    cn = int(0.18 * SR)
    clap = rng.standard_normal(cn) * env(cn, 0.001, 0.05)
    clap = clap - lowpass(clap, 900)
    # hat
    hn = int(0.05 * SR)
    hat = rng.standard_normal(hn) * env(hn, 0.0005, 0.012)
    hat = hat - lowpass(hat, 6000)

    beats = int(dur / BEAT)
    for b in range(beats):
        t = b * BEAT
        drop = cta - BEAT <= t < cta  # one-beat breakdown before the CTA
        if not drop:
            place(mix, kick, t, 0.9)
            if b % 2 == 1:
                place(mix, clap, t, 0.35)
        place(mix, hat, t + BEAT / 2, 0.12)
        place(mix, hat, t, 0.06)

    # sub bass + pad on Am F C G (one chord per bar = 2 s)
    roots = [55.0, 43.65, 65.41, 49.0]
    triads = [[220, 261.63, 329.63], [174.61, 220, 261.63], [196, 261.63, 329.63], [196, 246.94, 293.66]]
    for bar in range(int(np.ceil(dur / 2))):
        r, tri = roots[bar % 4], triads[bar % 4]
        for k in range(4):  # 8th-note pumping bass
            t0 = bar * 2 + k * 0.5
            ln = int(0.45 * SR)
            tt = np.arange(ln) / SR
            saw = 2 * ((tt * r) % 1) - 1
            place(mix, lowpass(saw, 300) * env(ln, 0.005, 0.25), t0, 0.35)
        ln = int(2 * SR)
        tt = np.arange(ln) / SR
        pad = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt) for f in tri)
        pad *= np.minimum(tt / 0.4, 1) * np.minimum((2 - tt) / 0.3, 1)
        place(mix, pad, bar * 2, 0.035)

    # whoosh + impact on every hit
    for h in hits:
        wn = int(0.35 * SR)
        w = rng.standard_normal(wn)
        w = lowpass(w, 2500) * np.sin(np.linspace(0, np.pi, wn)) ** 2
        place(mix, w, max(0, h - 0.3), 0.25)
        place(mix, kick, h, 0.5)

    # riser into the CTA
    rn = int(1.5 * SR)
    rt = np.arange(rn) / SR
    riser = rng.standard_normal(rn) * (rt / 1.5) ** 2
    riser = riser - lowpass(riser, 1500)
    riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 900 * (rt / 1.5) ** 2) / SR) * (rt / 1.5) ** 2
    place(mix, riser, cta - 1.5, 0.25)
    bn = int(1.5 * SR)
    boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-np.arange(bn) / SR * 8)) / SR) * env(bn, 0.001, 0.5)
    place(mix, boom, cta, 0.9)

    fade = int(0.6 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.4)
    mix *= 0.89 / np.max(np.abs(mix))
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main(sys.argv[1], json.loads(sys.argv[2]))
