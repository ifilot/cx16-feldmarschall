/* Real browser check of the website: the shipped WASM emulator, the game
 * files, keyboard, mouse and touch input, and the scaling of the screen.
 *   make site
 *   npm install --prefix build/browser-tools playwright@1.64.0
 *   NODE_PATH="$PWD/build/browser-tools/node_modules" node tests/check_site.cjs
 * Captures land in build/site-check/.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const site = path.join(root, 'build/site');
const captures = path.join(root, 'build/site-check');
fs.mkdirSync(captures, {recursive:true});
const prefix = '/cx16-feldmarschall';
const mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.wasm':'application/wasm',
  '.json':'application/json','.svg':'image/svg+xml','.png':'image/png'};
const server = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (!url.pathname.startsWith(prefix + '/')) {response.writeHead(404).end(); return;}
  const name = path.resolve(site, '.' + url.pathname.slice(prefix.length), url.pathname.endsWith('/') ? 'index.html' : '');
  if (!name.startsWith(site + path.sep) || !fs.existsSync(name)) {response.writeHead(404).end(); return;}
  response.setHeader('Content-Type', mime[path.extname(name)] || 'application/octet-stream');
  response.end(fs.readFileSync(name));
});

function python(script, ...args) {
  const result = spawnSync('python3', ['-c', script, ...args.map(String)], {encoding:'utf8'});
  if (result.error) throw result.error;
  return result;
}

// The canvas at exactly 640 x 480 page pixels. A phone screen is widened for
// the moment, so the page itself shows the game at its native size.
async function capture(page, name) {
  const file = path.join(captures, `${name}.png`);
  const canvas = page.locator('#canvas');
  const size = page.viewportSize();
  if (size.width < 700) {
    await page.setViewportSize({width:1280, height:size.height});
    await page.waitForFunction(() => canvas.getBoundingClientRect().width === 640);
  }
  await canvas.evaluate(element => {
    const rect = element.getBoundingClientRect();
    element.style.transform = `translate(${Math.ceil(rect.x) - rect.x}px, ${Math.ceil(rect.y) - rect.y}px)`;
  });
  // WebGL discards its drawing buffer; screenshot the composited canvas.
  await canvas.screenshot({path:file});
  await canvas.evaluate(element => { element.style.transform = ''; });
  if (size.width < 700) {
    await page.setViewportSize(size);
    await page.waitForFunction(width => canvas.getBoundingClientRect().width < width, size.width);
  }
  return file;
}

// Poll until a check on the captured screen passes: WASM start-up and scene
// changes depend on the speed of the host.
async function until(page, name, script, ...args) {
  const deadline = Date.now() + 30000;
  for (;;) {
    const file = await capture(page, name);
    const result = python(script, file, ...args);
    if (result.status === 0) return file;
    if (Date.now() >= deadline) assert.fail(`${name}: ${result.stderr.trim().split('\n').pop()} (see ${file})`);
    await page.waitForTimeout(250);
  }
}

// Decode the current exact 4 bpp tiled splash and its sixteen-color palette.
const SPLASH = `
import sys, numpy as np
from PIL import Image
shot, game = sys.argv[1:3]
pixels = np.asarray(Image.open(shot).convert('RGB'))
raw = np.frombuffer(open(f'{game}/SPLTIL.BIN','rb').read(), dtype=np.uint8)
tiles = np.stack([raw >> 4, raw & 15], axis=1).reshape(-1,8,8)
entries = np.frombuffer(open(f'{game}/SPLMAP.BIN','rb').read(), dtype='<u2').reshape(64,128)[:60,:80]
indices = tiles[entries & 1023].transpose(0,2,1,3).reshape(480,640)
pal = np.frombuffer(open(f'{game}/SPLPAL.BIN','rb').read(), dtype=np.uint8).reshape(16,2)
colors = np.stack([pal[:,1] & 15, pal[:,0] >> 4, pal[:,0] & 15], axis=1).astype(np.uint8)*17
ys, xs = np.nonzero(np.any(pixels != colors[indices], axis=2))
assert len(ys) == 0 or (np.ptp(ys) < 16 and np.ptp(xs) < 16), 'the splash screen does not match its tile assets'
`;
// Fraction of differing pixels of a box between two captures.
const CHANGED = `
import sys, numpy as np
from PIL import Image
a, b = (np.asarray(Image.open(f).convert('RGB')).astype(int) for f in sys.argv[1:3])
x, y, w, h = map(int, sys.argv[3:7])
low, high = float(sys.argv[7]), float(sys.argv[8])
changed = np.any(a[y:y+h, x:x+w] != b[y:y+h, x:x+w], axis=2).mean()
assert low <= changed <= high, f'{changed:.2f} of the box ({x},{y},{w},{h}) changed, expected {low}..{high}'
`;
// The screen of the main menu: the menu plate over the board, and an empty tray.
const MENU = `
import sys, numpy as np
from PIL import Image
pixels = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
plate = np.all(pixels[135:305, 85:345] == (187, 187, 170), axis=2).mean()
assert plate > 0.6, f'no menu plate ({plate:.2f})'
`;
// A box changed from 'before', and the boxes around it did not.
// Squares two away from E2, clear of the 64 x 64 hover brackets.
const NEIGHBOURS = [[96, 336], [256, 336], [176, 256]];
async function expectChange(page, name, before, box, others) {
  return until(page, name, `${CHANGED}
for x, y in [map(int, p.split(',')) for p in sys.argv[9:]]:
    changed = np.any(a[y:y+h, x:x+w] != b[y:y+h, x:x+w], axis=2).mean()
    assert changed == 0, f'the box at ({x},{y}) changed as well'
`, before, ...box, 0.3, 1, ...others.map(p => p.join(',')));
}

async function start(page) {
  await page.goto(`http://127.0.0.1:${server.address().port}${prefix}/`);
  assert.equal(await page.locator('h1').textContent(), 'Feldmarschall');
  return page;
}
async function boot(page, tap) {
  if (tap) await page.locator('#play').tap(); else await page.click('#play');
  await page.waitForFunction(() => typeof FS !== 'undefined' && Module.calledRun && !document.querySelector('#canvas').hidden);
  return until(page, `${page.label}-splash`, SPLASH, path.join(site, 'game'));
}

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || undefined, args:['--enable-unsafe-swiftshader']});
    const errors = [], failed = [];
    const watch = page => {
      page.on('pageerror', error => errors.push(error.message));
      page.on('response', response => { if (response.status() >= 400) failed.push(response.url()); });
      return page;
    };

    // Desktop: keyboard and mouse.
    const page = watch(await browser.newPage({viewport:{width:1280, height:1000}}));
    page.label = 'desktop';
    await start(page);
    await page.screenshot({path:path.join(captures, 'website.png'), fullPage:true});
    // The gallery opens each screenshot in the viewer, at a whole multiple.
    await page.locator('.shot').first().click();
    assert(await page.locator('#viewer').evaluate(dialog => dialog.open), 'the screenshot viewer did not open');
    await page.waitForFunction(() => document.getElementById('viewer-image').naturalWidth === 640);
    // 2x would not fit 1280 x 1000; the 6 px frame lies outside the pixels.
    assert.deepEqual(await page.locator('#viewer-image').evaluate(image => [image.clientWidth, image.clientHeight]), [640, 480]);
    await page.screenshot({path:path.join(captures, 'viewer.png')});
    await page.keyboard.press('ArrowRight');
    assert.match(await page.locator('#viewer-image').getAttribute('src'), /screens\/play\.png$/);
    assert.equal(await page.locator('#viewer-caption').textContent(), 'Battle the computer');
    await page.keyboard.press('Escape');
    assert(!(await page.locator('#viewer').evaluate(dialog => dialog.open)), 'Escape did not close the viewer');
    const splash = await boot(page);
    const manifest = JSON.parse(fs.readFileSync(path.join(site, 'game/manifest.json')));
    const loaded = await page.evaluate(() => FS.readdir('/'));
    for (const file of manifest.resources) assert(loaded.includes(file), `${file} missing from the emulator's file system`);
    assert.deepEqual(await page.evaluate(() => [canvas.width, canvas.height]), [640, 480]);
    assert.equal((await page.locator('#canvas').boundingBox()).width, 640);

    await page.locator('#canvas').press('Enter', {delay:100});
    const menu = await until(page, 'menu', MENU);
    await page.locator('#canvas').press('5', {delay:100});
    await until(page, 'about', CHANGED, menu, 85, 135, 260, 170, 0.05, 1);
    await page.locator('#canvas').press('Escape', {delay:100});
    await until(page, 'menu-again', MENU);

    const canvasBox = await page.locator('#canvas').boundingBox();
    const at = (x, y) => [canvasBox.x + x, canvasBox.y + y];
    await page.mouse.move(...at(320, 240));
    await page.waitForFunction(() => mouseAligned && !mouseAligning);
    await page.mouse.move(...at(175, 156), {steps:8});
    await page.waitForTimeout(300);
    await page.mouse.down(); await page.waitForTimeout(150); await page.mouse.up();
    // Manage setups: the tray fills with Red's pieces.
    const deploy = await until(page, 'deploy', CHANGED, menu, 432, 152, 200, 320, 0.3, 1);
    // Drag the Marshal from the first compartment onto E2.
    await page.mouse.move(...at(452, 172), {steps:10});
    await page.waitForTimeout(300);
    await page.mouse.down(); await page.waitForTimeout(150);
    await page.mouse.move(...at(196, 356), {steps:20});
    await page.waitForTimeout(300);
    await page.mouse.up(); await page.waitForTimeout(150);
    await page.mouse.move(...at(600, 20), {steps:10});
    await expectChange(page, 'deployed', deploy, [176, 336, 40, 40], NEIGHBOURS);
    await page.screenshot({path:path.join(captures, 'playing.png'), fullPage:true});

    // Fullscreen uses the largest whole pixel blocks.
    for (const [width, height, scale] of [[1920, 1080, 2], [1536, 864, 1]]) {
      await page.setViewportSize({width, height});
      await page.waitForTimeout(150);
      let box = await page.locator('#canvas').boundingBox();
      assert.equal(box.width, 640); assert.equal(box.height, 480);
      await page.click('#fullscreen');
      await page.waitForFunction(() => document.fullscreenElement?.id === 'player');
      await page.waitForTimeout(200);
      box = await page.locator('#canvas').boundingBox();
      assert.equal(box.width, 640 * scale); assert.equal(box.height, 480 * scale);
      assert.equal(box.x, Math.round(box.x)); assert.equal(box.y, Math.round(box.y));
      const file = path.join(captures, `fullscreen-${width}.png`);
      await page.locator('#canvas').screenshot({path:file});
      const result = python(`
import sys, numpy as np
from PIL import Image
pixels = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
k = int(sys.argv[2]); assert pixels.shape == (480 * k, 640 * k, 3)
blocks = pixels.reshape(480, k, 640, k, 3)
assert np.all(blocks == blocks[:, 0:1, :, 0:1, :]), 'fullscreen interpolates or uses uneven pixel blocks'
`, file, scale);
      assert.equal(result.status, 0, result.stderr);
      await page.evaluate(() => document.exitFullscreen());
      await page.waitForTimeout(150);
    }
    await page.setViewportSize({width:390, height:900});
    await page.waitForTimeout(200);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'the page overflows a phone screen');

    // Phone: the screen shrinks to fit, tap starts the game and a finger drags.
    const mobile = await browser.newContext({viewport:{width:390, height:844}, hasTouch:true, isMobile:true});
    const phone = watch(await mobile.newPage());
    phone.label = 'phone';
    await start(phone);
    await phone.screenshot({path:path.join(captures, 'mobile.png'), fullPage:true});
    assert(await phone.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'the page overflows a phone screen');
    assert.equal(await phone.locator('#touch-keys').count(), 0);
    await boot(phone, true);
    let box = await phone.locator('#canvas').boundingBox();
    assert(box.width < 390 && box.width > 300, `the screen does not fit the phone (${box.width} px)`);
    await phone.locator('#canvas').tap({position:{x:box.width/2,y:box.height/2}});
    const phoneMenu = await until(phone, 'phone-menu', MENU);
    const cdp = await mobile.newCDPSession(phone);
    const point = (x, y) => ({x:box.x + x * box.width / 640, y:box.y + y * box.height / 480});
    const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints:type === 'touchEnd' ? [] : [point(x, y)]});
    async function drag(from, to) {
      await phone.locator('#canvas').scrollIntoViewIfNeeded();
      box = await phone.locator('#canvas').boundingBox();
      await touch('touchStart', ...from);
      for (let i = 1; i <= 12; i++) {
        await touch('touchMove', from[0] + (to[0] - from[0]) * i / 12, from[1] + (to[1] - from[1]) * i / 12);
        await phone.waitForTimeout(30);
      }
      await phone.waitForTimeout(300);
      await touch('touchEnd');
    }
    await drag([175, 156], [175, 156]);
    const phoneDeploy = await until(phone, 'phone-deploy', CHANGED, phoneMenu, 432, 152, 200, 320, 0.3, 1);
    await drag([452, 172], [196, 356]);
    await expectChange(phone, 'phone-deployed', phoneDeploy, [176, 336, 40, 40], NEIGHBOURS);
    await phone.screenshot({path:path.join(captures, 'phone-playing.png'), fullPage:true});
    await mobile.close();

    assert.deepEqual(errors, []); assert.deepEqual(failed, []);
    console.log('PASS: WASM boot, all runtime files, exact splash pixels, keyboard and mouse menus, drag to deploy, '
      + 'whole-pixel fullscreen, and a fitted phone screen with tap-to-start and touch drag, under a project subpath.');
  } finally { if (browser) await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; server.close(); });
