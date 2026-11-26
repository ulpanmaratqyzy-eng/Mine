import json, os, subprocess, base64
R=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(R,"..","banners")
ADDR="📍 Қызылорда қ."
def b(name, bg, tag, head, body, cta, price=None, ctac="#b8395f", hs=104):
    pr=f'<div class="price">{price}</div>' if price else ''
    return {"path":os.path.join(OUT,name+".png"),"html":f'''<div class="bg" style="background-image:url(data:image/jpeg;base64,{base64.b64encode(open(f'{R}/frames/{bg}.jpg','rb').read()).decode()})"></div>
<div class="gt"></div><div class="gb"></div>
<div class="top"><span class="tag">{tag}</span><div class="h" style="font-size:{hs}px">{head}</div></div>
<div class="bot">{pr}<div class="body">{body}</div><div class="addr">{ADDR}</div><div class="cta" style="background:{ctac}">{cta}</div></div>'''}
items=[
 b("massage-1","m1","Скульптурный массаж","Жас көрінудің<br>ең тиімді,<br><span class='hl'>уколсыз</span> жолы","✓ Бет пішіні айқындалады<br>✓ Ісіну кетеді, тері сергиді","Директке «МАССАЖ» жаз",ctac="#7a1f3d"),
 b("massage-2","m2","Скульптурный массаж","Ботокссыз<br>лифтинг-эффект 🤍","Инъекциясыз · ауырсынусыз<br>Әсері алғашқы сеанстан-ақ","Директке «МАССАЖ» жаз",ctac="#7a1f3d"),
 b("massage-3","m3","Уколдан қорқасыз ба?","Укол салдырмай-ақ<br>жасаруға<br>болады ✨","Скульптурный массаж — тек<br>шебер қолдың күші","Жазылу → Директ",ctac="#7a1f3d",hs=96),
 b("chistka-1","c1","Бетті тазалау · акция","Таза, тегіс<br>тері 🤍","Терең тазалау · ультрадыбыс · LED-маска","Директке «ЧИСТКА» жаз",price="5 000 ₸"),
 b("chistka-2","c2","Бетті тазалау · акция","Қара нүкте мен<br>бөртпеден<br>арыл","Тәжірибелі косметолог · стерильді құралдар","Директке «ЧИСТКА» жаз",price="5 000 ₸",hs=96),
 b("biorevit-1","b1","Акция · Қызылорда","Терің ылғалға<br>тойып жарқырасын 💧","Биоревитализация<br>+ бетті тазалау <b>СЫЙЛЫҚҚА</b> 🎁","Директке «АКЦИЯ» жаз",price="15 000 ₸"),
]
css='''*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;font-family:Montserrat,sans-serif;color:#fff;overflow:hidden}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
.gt{position:absolute;left:0;right:0;top:0;height:900px;background:linear-gradient(180deg,rgba(43,20,32,.85),rgba(43,20,32,.45) 55%,rgba(43,20,32,0))}
.gb{position:absolute;left:0;right:0;bottom:0;height:1050px;background:linear-gradient(0deg,rgba(43,20,32,.96),rgba(43,20,32,.82) 55%,rgba(43,20,32,0))}
.top{position:absolute;left:80px;right:80px;top:250px}
.tag{display:inline-block;background:#b8395f;font-weight:700;font-size:34px;letter-spacing:2px;padding:14px 30px;border-radius:999px;text-transform:uppercase}
.h{font-weight:900;line-height:1.02;letter-spacing:-2px;margin-top:30px;text-shadow:0 4px 24px rgba(0,0,0,.45)}
.hl{color:#ffc2d1}
.bot{position:absolute;left:80px;right:80px;bottom:340px}
.price{font-weight:900;font-size:200px;letter-spacing:-6px;line-height:.95}
.body{font-size:46px;font-weight:700;line-height:1.4;margin-top:18px}.body b{color:#ffc2d1}
.addr{font-size:38px;font-weight:600;color:#ffd9c6;margin-top:30px}
.cta{margin-top:40px;border-radius:999px;font-weight:800;font-size:50px;text-align:center;padding:36px 20px;box-shadow:0 10px 40px rgba(0,0,0,.35)}'''
jp=os.path.join(R,"ov","photo_banners.json")
json.dump({"css":css,"items":items},open(jp,"w"),ensure_ascii=False)
subprocess.run(["node",os.path.join(R,"render_ov.js"),jp],check=True)
