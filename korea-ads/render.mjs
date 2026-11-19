// Usage: node render.mjs [sheet|video|poster] [creativeId|all]
import { createRequire } from 'node:module'; const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';
const __dir = path.dirname(url.fileURLToPath(import.meta.url));
const mode = process.argv[2] || 'sheet', which = process.argv[3] || 'all';
const IDS = ['grant100','topik','parents','masters','steps','myth'];
const ids = which === 'all' ? IDS : which.split(',');
const FPS = 30, SUB = 3;
const browser = await chromium.launch();
const scratch = process.env.SCRATCH || path.join(__dir, 'out', 'tmp'); fs.mkdirSync(scratch, { recursive: true });
async function open(id, q='render=1') {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error(id, 'PAGEERROR', e.message));
  await page.goto(url.pathToFileURL(path.join(__dir, 'engine.html')).href + `?c=${id}&${q}`);
  await page.evaluate(() => window.ready);
  return page;
}
async function job(id) {
  if (mode === 'poster') {
    const page = await open(id, 'poster=1');
    const b64 = await page.evaluate(() => document.getElementById('out').toDataURL('image/png'));
    fs.writeFileSync(path.join(__dir, 'out/posters', `${id}.png`), Buffer.from(b64.split(',')[1], 'base64'));
    return page.close();
  }
  const page = await open(id);
  const dur = await page.evaluate(() => window.cr.dur);
  if (mode === 'sheet') {
    const times = (process.env.TIMES || '').split(',').filter(Boolean).map(Number);
    const ts = times.length ? times : Array.from({ length: 12 }, (_, i) => +(0.9 + i * (dur - 1) / 12).toFixed(2));
    const files = [];
    for (const [i, t] of ts.entries()) {
      await page.evaluate(t => window.seek(t), t);
      const b64 = await page.evaluate(() => window.grab(.85));
      const f = path.join(scratch, `${id}_${i}.jpg`); fs.writeFileSync(f, Buffer.from(b64.split(',')[1], 'base64')); files.push(f);
    }
    const args = []; files.forEach(f => args.push('-i', f));
    const cols = 6, rows = Math.ceil(files.length / cols);
    const lay = files.map((_, i) => `${(i % cols) * 270}_${Math.floor(i / cols) * 480}`).join('|');
    const scaled = files.map((_, i) => `[${i}:v]scale=270:480[s${i}]`).join(';');
    execFileSync('ffmpeg', ['-v', 'error', '-y', ...args, '-filter_complex', `${scaled};${files.map((_, i) => `[s${i}]`).join('')}xstack=inputs=${files.length}:layout=${lay}:fill=black`, path.join(scratch, `sheet_${id}.png`)]);
    console.log('sheet', id, ts.join(' '));
    return page.close();
  }
  // video
  const n = Math.round(dur * FPS);
  const silent = path.join(scratch, `${id}_silent.mp4`);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '18', '-movflags', '+faststart', silent], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < n; f++) {
    const b64 = await page.evaluate(([f, F, S]) => { window.frame(f, F, S); return window.grab(.94); }, [f, FPS, SUB]);
    if (!ff.stdin.write(Buffer.from(b64.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  const meta = await page.evaluate(() => ({ dur: window.cr.dur, cta: window.cr.cta, hits: window.cr.hits }));
  const wav = path.join(scratch, `${id}.wav`);
  execFileSync('python3', [path.join(__dir, 'audio.py'), wav, JSON.stringify(meta)]);
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', silent, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', path.join(__dir, 'out/videos', `${id}.mp4`)]);
  console.log('video', id, n, 'frames');
  await page.close();
}
await Promise.all(ids.map(job));
await browser.close();
