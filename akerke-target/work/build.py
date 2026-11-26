#!/usr/bin/env python3
"""Build 9:16 target videos for Akerke Cosmet from real footage.
Hard cuts, static text plates (no animation)."""
import json, subprocess, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "..", "src")
OUT = os.path.join(ROOT, "..", "videos")
OV = os.path.join(ROOT, "ov")
os.makedirs(OUT, exist_ok=True); os.makedirs(OV, exist_ok=True)

CITY = "Қызылорда"

def brand():
    return '<div class="brand">AKERKE COSMET</div>'

def head(big, small=None, top=430, size=108):
    s = f'<div class="lbl">{small}</div>' if small else ''
    return f'<div class="head" style="top:{top}px">{s}<div class="big" style="font-size:{size}px">{big}</div></div>'

def plate(lines, top=1080):
    return f'<div class="plate" style="top:{top}px">' + ''.join(f'<div>{l}</div>' for l in lines) + '</div>'

def sub(text):
    return f'<div class="sub">{text}</div>'

def end(title, price, extra, cta, cta_color="#b8395f"):
    p = f'<div class="eprice">{price}</div>' if price else ''
    return f'''<div class="shade"></div>
<div class="endc">
  <div class="etitle">{title}</div>{p}
  <div class="eextra">{extra}</div>
  <div class="eaddr">📍 {CITY} қ.</div>
  <div class="ecta" style="background:{cta_color}">{cta}</div>
</div>'''

# ---------------- VIDEO SPECS ----------------
VO_FILES = ["vo1","vo2","vo3","voA","voB","vo5","voC"]
VO = [4.128, 4.896, 4.224, 4.656, 3.864, 2.520, 3.312]
VO_TXT = [
    "Қызылордалық сұлулар, қыста теріңіз құрғап, бозарып жүр ме?",
    "Биоревитализация — теріні ішінен ылғалға толтыратын процедура.",
    "Ұсақ әжімдер тегістеліп, бет табиғи жарқылға ие болады.",
    "Білікті маман — косметолог Акеркеде арнайы шектеулі акция!",
    "Биоревитализация небәрі 15 000 теңге,",
    "ал бетті тазалау — сыйлыққа!",
    "Жазылу үшін директке «Акция» деп жазыңыз.",
]
t = 0.3; VO_T = []
for d in VO:
    VO_T.append((t, t + d)); t += d + 0.3
A_LEN = round(t + 0.5, 2)

videos = {
 "1_biorevit_chistka_sylyq": {
   "clips": [("v2c.mp4",0.0,3.0),("v3c.mp4",4.7,1.2),("v3c.mp4",8.4,0.9),("v3c.mp4",13.9,1.2),
             ("v2c.mp4",4.3,2.0),("v3c.mp4",16.7,1.2),("v3c.mp4",35.0,0.7),("v2c.mp4",9.5,2.5),
             ("v4c.mp4",15.4,1.4),("v1c.mp4",53.0,1.6),("v1c.mp4",47.2,1.5),("v3c.mp4",26.7,1.0),
             ("v4c.mp4",49.7,1.5),("v2c.mp4",6.3,2.0),("v4c.mp4",45.5,1.7),("v1c.mp4",13.5,2.0),
             ("v3c.mp4",27.7,0.8),("v4c.mp4",60.6,1.1),("v4c.mp4",61.9,1.8),("v2c.mp4",12.0,round(A_LEN-29.1,2))],
   "vo": True,
   "ov": [
     (0, VO_T[6][0]-0.3, brand()),
     (VO_T[0][0], VO_T[1][0], head("Терің құрғап<br>жүр ме? 💧")),
     (VO_T[1][0], VO_T[3][0], head("БИОРЕВИТА-<br>ЛИЗАЦИЯ", "ылғал · жарқыл · тегіс тері")),
     (VO_T[3][0], VO_T[4][0], head("Косметолог<br>Акерке", "білікті маман") + plate(['Арнайы <b>шектеулі акция</b> ⏳'], top=760)),
     (VO_T[4][0], VO_T[6][0]-0.3, head('15 000 ₸', 'биоревитализация', size=160) + plate(['+ бетті тазалау <b>СЫЙЛЫҚҚА</b> 🎁'], top=760)),
   ] + [(a, b, sub(VO_TXT[i])) for i,(a,b) in enumerate(VO_T[:6])] + [
     (VO_T[6][0]-0.3, A_LEN, end("Биоревитализация", "15 000 ₸", "+ бетті тазалау сыйлыққа 🎁<br>Білікті маман Акерке · орын шектеулі ⏳", "Директке «АКЦИЯ» жаз")),
   ],
 },
 "2_chistka_5000": {
   "clips": [("v3c.mp4",45.9,1.9),("v1c.mp4",0.5,1.5),("v3c.mp4",27.7,1.1),("v1c.mp4",13.5,2.0),
             ("v3c.mp4",37.4,1.0),("v3c.mp4",39.5,0.8),("v1c.mp4",47.2,2.0),("v1c.mp4",67.5,2.0),
             ("v3c.mp4",49.1,1.5),("v1c.mp4",128.5,2.0),("v4c.mp4",49.7,1.8),("v4c.mp4",61.9,1.8),
             ("v3c.mp4",4.7,0.9)],
   "ov": [
     (0, 15.8, brand()),
     (0, 3.4, head("5 000 ₸", "БЕТТІ ТАЗАЛАУ · АКЦИЯ", size=180)),
     (3.4, 10.3, plate(["✓ Терең тазалау","✓ Қара нүкте мен бөртпеден арылу"])),
     (10.3, 15.8, plate(["✓ Аппараттық күтім","✓ LED-маска","✓ Тері тыныстап, жарқырайды"])),
     (15.8, 20.3, end("Бетті тазалау", "5 000 ₸", "Акция уақыты шектеулі ⏳", "Директке «ЧИСТКА» жаз")),
   ],
 },
 "3a_massage_ukolsyz": {
   "clips": [("v4c.mp4",3.0,1.7),("v4c.mp4",5.0,2.0),("v4c.mp4",9.4,1.4),("v4c.mp4",11.0,1.3),
             ("v4c.mp4",15.4,1.4),("v4c.mp4",17.0,1.7),("v4c.mp4",20.2,2.3),("v4c.mp4",25.5,1.4),
             ("v4c.mp4",27.1,1.9),("v4c.mp4",58.9,1.5),("v4c.mp4",60.6,1.1),("v4c.mp4",61.9,1.8)],
   "ov": [
     (0, 16.7, brand()),
     (0, 3.7, head("Жас көрінудің<br>ең тиімді,<br><span class='hl'>УКОЛСЫЗ</span> жолы")),
     (3.7, 9.5, head("СКУЛЬПТУРНЫЙ<br>МАССАЖ", size=86) + plate(["✓ Бет пішіні айқындалады","✓ Ісіну кетеді"])),
     (9.5, 16.7, plate(["✓ Тері тартылып, сергиді","✓ Әсері алғашқы сеанстан-ақ"])),
     (16.7, 19.6, end("Скульптурный массаж", None, "Инъекциясыз · ауырсынусыз 🤍", "Директке «МАССАЖ» жаз", "#7a1f3d")),
   ],
 },
 "3b_massage_botokssyz": {
   "clips": [("v4c.mp4",30.2,2.0),("v4c.mp4",12.5,0.7),("v4c.mp4",13.4,0.6),("v4c.mp4",14.1,1.1),
             ("v4c.mp4",18.9,1.1),("v4c.mp4",22.7,2.6),("v4c.mp4",35.3,1.5),("v4c.mp4",47.4,2.1),
             ("v4c.mp4",58.9,1.5),("v4c.mp4",61.9,1.8),("v4c.mp4",15.4,0.9)],
   "ov": [
     (0, 11.7, brand()),
     (0, 4.4, head("Ботокссыз<br>лифтинг-эффект")),
     (4.4, 8.1, plate(["Инъекциясыз, ауырсынусыз","тек шебер қолдың күші 🤍"])),
     (8.1, 11.7, plate(["Бет пішіні айқын,","тері жас әрі сергек ✨"])),
     (11.7, 15.9, end("Скульптурный массаж", None, "Жас көрінудің уколсыз жолы", "Директке «МАССАЖ» жаз", "#7a1f3d")),
   ],
 },
}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:transparent;font-family:Montserrat,sans-serif;color:#fff}
.brand{position:absolute;top:250px;left:80px;font-weight:700;font-size:30px;letter-spacing:5px;padding:14px 28px;border-radius:999px;background:rgba(43,20,32,.55)}
.head{position:absolute;left:80px;right:80px}
.lbl{display:inline-block;font-weight:700;font-size:34px;letter-spacing:3px;background:#b8395f;padding:12px 26px;border-radius:14px;margin-bottom:22px}
.big{font-weight:900;font-size:108px;line-height:1.02;letter-spacing:-2px;text-shadow:0 6px 30px rgba(0,0,0,.55),0 2px 6px rgba(0,0,0,.5)}
.hl{color:#ffd0dc}
.plate{position:absolute;left:80px;right:80px;background:rgba(43,20,32,.78);border-radius:36px;padding:34px 44px;font-size:48px;font-weight:700;line-height:1.45}
.plate b{color:#ffb7c9}
.sub{position:absolute;left:90px;right:90px;bottom:380px;text-align:center;font-size:42px;font-weight:700;line-height:1.3;
 background:rgba(0,0,0,.55);border-radius:22px;padding:18px 26px}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(43,20,32,.35),rgba(43,20,32,.82) 45%,rgba(43,20,32,.9))}
.endc{position:absolute;left:80px;right:80px;top:330px;bottom:340px;display:flex;flex-direction:column;justify-content:center}
.etitle{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:100px;line-height:1}
.eprice{font-weight:900;font-size:190px;letter-spacing:-5px;line-height:1;margin-top:20px}
.eextra{font-size:46px;font-weight:600;margin-top:30px;line-height:1.4}
.eaddr{font-size:44px;font-weight:700;margin-top:50px;line-height:1.35;color:#ffd9c6}
.ecta{margin-top:60px;border-radius:999px;font-weight:800;font-size:50px;text-align:center;padding:38px 20px}
"""

def render_overlays(name, spec):
    items = []
    for i,(a,b,html) in enumerate(spec["ov"]):
        path = os.path.join(OV, f"{name}_{i}.png")
        items.append({"path": path, "html": html})
    job = {"css": CSS, "items": items}
    jp = os.path.join(OV, f"{name}.json")
    json.dump(job, open(jp,"w"), ensure_ascii=False)
    subprocess.run(["node", os.path.join(ROOT,"render_ov.js"), jp], check=True)
    return [it["path"] for it in items]

def build(name, spec):
    pngs = render_overlays(name, spec)
    args = ["ffmpeg","-v","error","-y"]
    fc = []
    for i,c in enumerate(spec["clips"]):
        src,ss,d = c[:3]; pre = (c[3] + ",") if len(c) > 3 and c[3] else ""
        args += ["-ss",str(ss),"-t",str(d),"-i",os.path.join(SRC,src)]
        fc.append(f"[{i}:v]{pre}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p,trim=duration={d},setpts=PTS-STARTPTS[c{i}]")
    n = len(spec["clips"])
    fc.append("".join(f"[c{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[base]")
    total = round(sum(c[2] for c in spec["clips"]), 3)
    last = "base"
    for j,p in enumerate(pngs):
        idx = n + j
        args += ["-i", p]
        a,b,_ = spec["ov"][j]
        fc.append(f"[{last}][{idx}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[o{j}]")
        last = f"o{j}"
    k = n + len(pngs)
    args += ["-i", os.path.join(ROOT,"pad.wav")]
    if spec.get("vo"):
        vo_in = []
        vol = spec.get("vo_list") or [(VO_FILES[i], a) for i,(a,_) in enumerate(VO_T)]
        for i,(vf,a) in enumerate(vol):
            args += ["-i", os.path.join(ROOT, vf + ".mp3")]
            ms = int(a*1000)
            fc.append(f"[{k+1+i}:a]aresample=44100,adelay={ms}|{ms},apad=whole_dur={total}[v{i}]")
            vo_in.append(f"[v{i}]")
        fc.append("".join(vo_in) + f"amix=inputs={len(vo_in)}:normalize=0,volume=2.0[vo]")
        fc.append(f"[{k}:a]atrim=duration={total},volume=0.35,afade=t=out:st={total-1.5}:d=1.5[bg]")
        fc.append("[vo][bg]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]")
    else:
        fc.append(f"[{k}:a]atrim=duration={total},volume=3.6,afade=t=out:st={total-1.5}:d=1.5[aout]")
    out = os.path.join(OUT, f"{name}.mp4")
    args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[aout]",
             "-t", str(total), "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","160k","-movflags","+faststart", out]
    subprocess.run(args, check=True)
    print("built", out, round(total,2), "s")

if __name__ == "__main__":
    names = sys.argv[1:] or list(videos)
    for nm in names:
        build(nm, videos[nm])
