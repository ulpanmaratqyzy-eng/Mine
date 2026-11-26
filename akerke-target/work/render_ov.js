const {chromium} = require('playwright');
const fs = require('fs');
(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1080, height: 1920}});
  for (const it of job.items) {
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Cormorant+Garamond:wght@700&display=swap" rel="stylesheet">
<style>${job.css}</style></head><body>${it.html}</body></html>`, {waitUntil: 'networkidle'});
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(150); await p.screenshot({path: it.path, omitBackground: true});
  }
  await b.close();
})();
