// Screenshot helper for docs: node scripts/screenshot.mjs URL out.png [width height]
import { createRequire } from 'module'; const require = createRequire(process.cwd() + '/package.json'); const { chromium } = require('playwright-core');
const [,, url, out, w = 1280, h = 1500] = process.argv;
const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const p = await b.newPage({ viewport: { width: +w, height: +h } }); await p.goto(url); await p.waitForTimeout(1500);
await p.screenshot({ path: out, fullPage: true }); await b.close();
