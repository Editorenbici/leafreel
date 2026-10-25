// Records a real session of the web app (Playwright video) and writes marker times for editing.
// Usage: CHROMIUM_PATH=... node scripts/record_demo.mjs http://127.0.0.1:8100 OUT_DIR [style] [sample]
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import { execFileSync } from 'child_process';
const require = createRequire(process.cwd() + '/package.json'); const { chromium } = require('playwright-core');
const [,, base, out, style = 'papercut', sample = 'volcanoes'] = process.argv; fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: 1024, height: 576 } });
const page = await ctx.newPage(); const marks = {}; const mark = (k) => { marks[k] = Date.now() / 1000; console.log(k); };
// Screen capture through the DevTools screencast (no extra binaries): frames + timestamps, assembled with the system ffmpeg at the end.
fs.mkdirSync(path.join(out, 'frames'), { recursive: true }); const stamps = [];
const cdp = await ctx.newCDPSession(page);
cdp.on('Page.screencastFrame', async ({ data, metadata, sessionId }) => { fs.writeFileSync(path.join(out, 'frames', `${stamps.length}.jpg`), Buffer.from(data, 'base64')); stamps.push(metadata.timestamp); await cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {}); });
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 82, maxWidth: 1024, maxHeight: 576, everyNthFrame: 1 });
const sleep = (ms) => page.waitForTimeout(ms);
await page.goto(base); await sleep(1800); mark('start');
await page.click(`.sample[data-f=${sample}]`); await sleep(1200);
await page.evaluate(() => window.scrollTo({ top: 420, behavior: 'smooth' })); await sleep(1200); mark('styles');
for (const el of await page.$$('.style')) { await el.hover(); await sleep(900); }
await page.click(`.style[data-id=${style}]`); await sleep(800);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await sleep(800); mark('press');
await page.click('#go'); await sleep(1500); mark('running');
await page.waitForSelector('#result:not(.hide)', { timeout: 25 * 60 * 1000 }); mark('done'); await sleep(1500);
await page.evaluate(() => document.querySelector('#player').scrollIntoView({ behavior: 'smooth', block: 'center' })); await sleep(800);
await page.evaluate(() => { const v = document.querySelector('#player'); v.muted = true; v.play(); }); await sleep(5000); mark('played');
await page.evaluate(() => { const v = document.querySelector('#player'); v.pause(); });
await page.click('#facts'.replace('#facts', 'details:has(#facts) summary')); await sleep(2500); mark('facts');
await page.click('details#editor summary'); await sleep(1500);
const first = await page.$('.ed .n'); await first.click({ clickCount: 3 }); await page.keyboard.type('Meet Mia, a curious explorer who wants to understand what is happening deep inside our planet.', { delay: 25 }); await sleep(800); mark('edited');
await page.click('#remake'); await sleep(1500); mark('remake');
await page.waitForSelector('#result:not(.hide)', { timeout: 25 * 60 * 1000 }); await sleep(400);
await page.waitForFunction(() => document.querySelector('#progress').classList.contains('hide') && !document.querySelector('#result').classList.contains('hide'), { timeout: 25 * 60 * 1000 }); mark('remade'); await sleep(2500);
await cdp.send('Page.stopScreencast'); await sleep(300);
const t0 = stamps[0]; const rel = Object.fromEntries(Object.entries(marks).map(([k, v]) => [k, +(v - t0).toFixed(2)]));
fs.writeFileSync(path.join(out, 'marks.json'), JSON.stringify(rel, null, 1));
fs.writeFileSync(path.join(out, 'list.txt'), stamps.map((t, i) => `file 'frames/${i}.jpg'\nduration ${Math.max(0.02, (stamps[i + 1] ?? t + 0.5) - t).toFixed(4)}`).join('\n') + '\n');
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(out, 'list.txt'), '-vf', 'fps=25,scale=1280:720,format=yuv420p', '-c:v', 'libx264', '-crf', '20', path.join(out, 'rec.mp4')]);
await ctx.close(); await browser.close(); console.log('saved', stamps.length, 'frames');
