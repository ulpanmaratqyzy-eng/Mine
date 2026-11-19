# Корея гранттары — 9:16 таргет креативтері

## Стиль таңдауы

[awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) базасынан **@techhalla "kinetic street-poster"** промпты алынды
(`prompts/techhalla-498547.md`). Неге дәл осы:

- Үлгі видеодағыдай: қара фон, **ірі кең сары тақырыптар**, әр сөз битке түседі.
- Алғашқы 1 секундта «hook» бар (лента айналдыруды тоқтатады).
- Нақты сандарға (грант %, бағалар) және соңғы CTA-ға лайықты.

Қосымша `@verbove` промптынан алынған техникалар: бір `draw(t)` функциясы, пружиналар, контакт-парақ арқылы алдын ала тексеру.

## Бейімделген промпт (қайта қолдануға болады)

```text
You are a world-class motion designer making a 15.00s vertical ad for a Kazakhstan
study-abroad agency: grants at South Korean universities. Showreel stakes.

FORMAT: one HTML file, 1080×1920 (9:16), 30fps export with 3 sub-frames motion blur.
Safe zone: all key content between y=300 and y=1500 (Reels/TikTok UI covers the rest).

PALETTE (strict): bg #0B0D14 · yellow #FFD83D · white #F5F3EE ·
taegeuk red #E8344E + blue #2F5BEA ONLY as print-misregistration (±4px) on impact frames.

TYPE: Roboto Flex 1000 ultra-expanded for 1–4 word screams (must support Kazakh
ә ғ қ ң ө ұ ү һ і); Roboto Flex condensed for numbers; Montserrat for small print.
A giant outlined Hangul word (Black Han Sans) drifts in the background at 5% opacity.

MESSAGE: Kazakh only. Exact facts from the agency guide — no invented numbers.
Every grant number gets a footnote "* depends on university, TOPIK/IELTS, GPA".

ARC (15s, 120 BPM, downbeat at t=0):
0–2.5s  HOOK — audience call-out crumb + 2–3 word slam with spring overshoot.
2.5–4.5 TWIST — question → answer in a yellow highlight bar.
4.5–10s PROOF — university cards / TOPIK ladder / price rows land on beats, counters roll.
10–12.5 CONDITIONS or EMOTIONAL LINE.
12.5–15 CTA — "ТЕГІН КОНСУЛЬТАЦИЯ", pulsing yellow button "ЖАЗЫЛУ →",
         "Директке «КОДОВОЕ СЛОВО» деп жаз" (a different keyword per creative = tracking).

TECHNIQUES: seek(t) pure function of time; closed-form springs; per-glyph stagger;
smash-pan exits with blur; punch-in camera (1.0→1.045) on hit times; beat-tick
progress bar under the header; film grain; synthesized 120 BPM soundtrack
(kick, clap, hats, Am–F–C–G bass, riser + boom into the CTA).
Pre-pass: contact sheet of 12 frames, fix cramped type, then render.

BANNED: stock "graduation cap" clipart, gradients on UI, emoji, long paragraphs,
promises like "100% guaranteed grant".
```

## 6 креатив: hook × аудитория

| # | Файл | Аудитория | Hook | Кодтық сөз |
|---|------|-----------|------|-----------|
| 1 | `grant100` | 11-сынып / талапкерлер 16–19 | «Кореяда ТЕГІН ОҚУ → Шын ба? Иә. 100%-ға дейін» | ГРАНТ |
| 2 | `topik` | Корей тілін оқитындар, K-pop/дорама 15–24 | «Корей тілін оқисың ба? → Әр TOPIK деңгейі = жеңілдік» | TOPIK |
| 3 | `parents` | Ата-аналар 35–55 | «Балам Кореяда оқыса, қанша тұрады?» | ЕСЕП |
| 4 | `masters` | Бакалавр түлектері 21–30 | «Диплом бар. Ал енді? → Магистратура Сеулде» | МАГИСТР |
| 5 | `steps` | Жылы аудитория / ретаргет | «Грант алудың 3 қадамы» (сақтап қой) | ЖОСПАР |
| 6 | `myth` | Бюджетке қарайтын жастар 17–25 | «Кореяда оқу — ҚЫМБАТ? → МИФ.» | КОРЕЯ |

Әр креативте **әртүрлі кодтық сөз** — директке келген хабарлама арқылы қай креатив/аудитория жұмыс істегенін бірден көресіз.

## Қайта рендерлеу

```bash
node render.mjs sheet all     # тексеру үшін контакт-парақ
node render.mjs poster all    # out/posters/*.png
node render.mjs video all     # out/videos/*.mp4 (музыкамен)
```

`engine.html?c=topik` — браузерде ашып, анимацияны тікелей көруге болады.
Мәтінді өзгерту үшін `engine.html` ішіндегі `CR.<id>` блогын түзетіңіз.

Шрифттер: Roboto Flex, Montserrat, Black Han Sans — SIL Open Font License.
