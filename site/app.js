'use strict';
const canvas = document.getElementById('canvas');
const status = document.getElementById('status');
const play = document.getElementById('play');
const player = document.getElementById('player');
const viewport = document.getElementById('game-viewport');
const screen = document.getElementById('screen');
let started = false;
function fail(message) {
  status.textContent = 'Unable to start the game';
  const error = document.getElementById('error');
  error.textContent = `${message} Reload to try again, or download the game to play in a desktop emulator.`;
  error.hidden = false;
  play.disabled = false;
  play.textContent = 'Reload and try again';
  play.onclick = () => location.reload();
}
// The release's Emscripten runtime reads this global before it starts.
var Module = {
  canvas,
  arguments: ['-prg', 'FELDMARS.PRG', '-run', '-ram', '512', '-scale', '1', '-quality', 'nearest', '-keymap', 'en-us', '-joy1'],
  locateFile: name => `emulator/${name}`,
  preRun: [function () {
    ENV.SDL_EMSCRIPTEN_KEYBOARD_ELEMENT = '#canvas';
    addRunDependency('feldmarschall-manifest');
    fetch('game/manifest.json').then(response => {
      if (!response.ok) throw new Error('The game files could not be downloaded.');
      return response.json();
    }).then(manifest => {
      for (const name of manifest.resources) {
        FS.createPreloadedFile('/', name, `game/${name}`, true, true, undefined,
          () => fail(`The file ${name} could not be downloaded.`));
      }
      removeRunDependency('feldmarschall-manifest');
    }).catch(error => fail(error.message));
  }],
  postRun: [function () {
    document.getElementById('cover').hidden = true;
    canvas.hidden = false;
    status.textContent = 'Game running';
    document.getElementById('fullscreen').disabled = false;
    document.getElementById('restart').disabled = false;
    Module.ccall('j2c_start_audio', 'void', ['bool'], [true]);
    resumeAudio();
    updateDisplay();
    canvas.focus({preventScroll: true});
  }],
  print: text => console.log(text),
  printErr: text => console.warn(text),
  setStatus: text => { if (text) status.textContent = 'Loading the emulator…'; },
  onAbort: () => fail('The emulator stopped before the game could start.')
};
play.addEventListener('click', () => {
  if (started) return;
  started = true;
  play.disabled = true;
  play.textContent = 'Loading…';
  status.textContent = 'Loading the game and emulator…';
  const script = document.createElement('script');
  script.src = 'emulator/x16emu.js';
  script.onerror = () => fail('The emulator could not be downloaded.');
  document.body.append(script);
});
function resumeAudio() {
  Module.SDL2?.audioContext?.resume().catch(() => {});
}
canvas.addEventListener('pointerdown', resumeAudio);
canvas.addEventListener('click', () => {
  canvas.focus({preventScroll: true});
  resumeAudio();
});
canvas.addEventListener('keydown', event => {
  resumeAudio();
  if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' ','Backspace','Tab'].includes(event.key)) event.preventDefault();
});
canvas.addEventListener('contextmenu', event => event.preventDefault());
canvas.addEventListener('webglcontextlost', event => {
  event.preventDefault();
  fail('The browser lost its graphics context.');
});
document.getElementById('fullscreen').addEventListener('click', async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await player.requestFullscreen();
    canvas.focus({preventScroll: true});
  } catch { status.textContent = 'Fullscreen is unavailable in this browser'; }
});
document.getElementById('exit-fullscreen').addEventListener('click', async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  canvas.focus({preventScroll: true});
});
document.getElementById('restart').addEventListener('click', () => location.reload());
fetch('build.json').then(response => response.json()).then(info => {
  document.getElementById('version').textContent = `v${info.version.replace(/^v/, '')} · ${info.commit.slice(0, 7)}`;
}).catch(() => {});

// The emulator turns host pointer positions into relative PS/2 movement, and
// the ROM's pointer starts centered while SDL's first host coordinate is zero.
// Drive both into the corner, where the KERNAL clamps, before accepting the
// first browser movement. Small steps avoid overwhelming the PS/2 queue.
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
let mouseAligned = false;
let mouseAligning = false;
function moveTo(x, y) {
  const rect = canvas.getBoundingClientRect();
  canvas.dispatchEvent(new MouseEvent('mousemove', {bubbles:true,
    clientX:rect.left + x * rect.width / 640, clientY:rect.top + y * rect.height / 480}));
}
async function alignMouse(x, y) {
  if (mouseAligned || mouseAligning) return;
  mouseAligning = true;
  for (let step = 1; step <= 10; step++) { moveTo(64 * step, 48 * step); await wait(40); }
  for (let step = 9; step >= 0; step--) { moveTo(64 * step, 48 * step); await wait(40); }
  for (let step = 1; step <= 4; step++) { moveTo(x * step / 4, y * step / 4); await wait(40); }
  mouseAligned = true;
  mouseAligning = false;
}
function nativePoint(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  return {x:(clientX - rect.left) * 640 / rect.width, y:(clientY - rect.top) * 480 / rect.height};
}
canvas.addEventListener('mousemove', event => {
  if (!event.isTrusted || mouseAligned) return;
  event.stopImmediatePropagation();
  const point = nativePoint(event.clientX, event.clientY);
  alignMouse(point.x, point.y);
}, true);
for (const type of ['mousedown','mouseup']) canvas.addEventListener(type, event => {
  if (mouseAligning) event.stopImmediatePropagation();
}, true);

// The framebuffer stays at its native size on the desktop and shrinks to fit
// narrow screens. Fullscreen uses whole physical-pixel multiples when they fit.
function updateDisplay() {
  const fullscreen = document.fullscreenElement === player;
  const dpr = window.devicePixelRatio || 1;
  const border = fullscreen ? 0 : 12;
  const room = viewport.clientWidth - border;
  let scale = Math.min(1, room / 640);
  if (fullscreen) {
    const width = viewport.clientWidth, height = viewport.clientHeight;
    const whole = Math.floor(Math.min(width * dpr / 640, height * dpr / 480));
    scale = whole >= 1 ? whole / dpr : Math.min(width / 640, height / 480);
  }
  const width = Math.floor(640 * scale), height = Math.floor(480 * scale);
  screen.style.width = canvas.style.width = `${width}px`;
  screen.style.height = canvas.style.height = `${height}px`;
  screen.style.marginLeft = `${Math.max(0, Math.floor((viewport.clientWidth - width - border) / 2))}px`;
  screen.style.marginTop = `${fullscreen ? Math.max(0, Math.floor((viewport.clientHeight - height) / 2)) : 0}px`;
  screen.style.transform = '';
  // Centered blocks and text above the game can introduce half-pixel origins.
  const rect = screen.getBoundingClientRect();
  const x = rect.left + border / 2, y = rect.top + border / 2;
  screen.style.transform = `translate(${Math.round(x * dpr) / dpr - x}px, ${Math.round(y * dpr) / dpr - y}px)`;
}
let displayFrame;
function scheduleDisplay() {
  cancelAnimationFrame(displayFrame);
  displayFrame = requestAnimationFrame(updateDisplay);
}
window.addEventListener('resize', scheduleDisplay);
document.addEventListener('fullscreenchange', scheduleDisplay);
window.visualViewport?.addEventListener('resize', scheduleDisplay);
new ResizeObserver(scheduleDisplay).observe(player);
updateDisplay();

// The game is played by dragging, so one finger is the mouse: touching presses
// the button where the finger lands, moving drags and lifting releases. The
// actions run in order; pending moves merge so a slow emulator never lags far
// behind the finger. SDL's own touch handling is kept out of the way.
const actions = [];
let pointer = null;
let working = false;
function act(action) {
  const last = actions[actions.length - 1];
  if (action.type === 'move' && last?.type === 'move') actions[actions.length - 1] = action;
  else actions.push(action);
  if (!working) work();
}
async function work() {
  working = true;
  while (actions.length) {
    const action = actions.shift();
    if (action.type === 'move') {
      if (!mouseAligned) await alignMouse(action.x, action.y);
      else {
        const from = pointer || action;
        const steps = Math.max(1, Math.ceil(Math.max(Math.abs(action.x - from.x), Math.abs(action.y - from.y)) / 64));
        for (let step = 1; step <= steps; step++) {
          moveTo(from.x + (action.x - from.x) * step / steps, from.y + (action.y - from.y) * step / steps);
          if (steps > 1) await wait(40);
        }
      }
      pointer = {x:action.x, y:action.y};
      await wait(20);
    } else {
      const rect = canvas.getBoundingClientRect();
      canvas.dispatchEvent(new MouseEvent(action.type, {bubbles:true, button:0, buttons:action.type === 'mousedown' ? 1 : 0,
        clientX:rect.left + pointer.x * rect.width / 640, clientY:rect.top + pointer.y * rect.height / 480}));
      // The game samples the buttons once per 60 Hz frame.
      await wait(60);
    }
  }
  working = false;
}
let finger = null;
for (const type of ['touchstart','touchmove','touchend','touchcancel']) {
  canvas.addEventListener(type, event => {
    event.stopImmediatePropagation();
    event.preventDefault();
    const touch = [...event.changedTouches].find(t => finger === null ? true : t.identifier === finger);
    if (!touch) return;
    const point = nativePoint(touch.clientX, touch.clientY);
    point.x = Math.max(0, Math.min(639, point.x));
    point.y = Math.max(0, Math.min(479, point.y));
    if (type === 'touchstart' && finger === null && event.touches.length === 1) {
      finger = touch.identifier;
      canvas.focus({preventScroll: true});
      act({type:'move', ...point});
      act({type:'mousedown'});
    } else if (type === 'touchmove' && finger !== null) {
      act({type:'move', ...point});
    } else if ((type === 'touchend' || type === 'touchcancel') && finger !== null) {
      finger = null;
      act({type:'move', ...point});
      act({type:'mouseup'});
    }
  }, {capture:true, passive:false});
}

// Screenshots open in a viewer at whole pixel multiples where they fit. The
// links still lead to the plain images without JavaScript.
const viewer = document.getElementById('viewer');
const viewerImage = document.getElementById('viewer-image');
const shots = [...document.querySelectorAll('.shot')];
let shown = 0;
function sizeViewer() {
  const dpr = window.devicePixelRatio || 1;
  const width = innerWidth - 44, height = innerHeight - 90;
  const whole = Math.floor(Math.min(width * dpr / 640, height * dpr / 480));
  const scale = whole >= 1 ? whole / dpr : Math.min(width / 640, height / 480);
  viewerImage.style.width = `${Math.floor(640 * scale)}px`;
  viewerImage.style.height = `${Math.floor(480 * scale)}px`;
}
function showShot(index) {
  shown = (index + shots.length) % shots.length;
  const image = shots[shown].querySelector('img');
  viewerImage.src = shots[shown].href;
  viewerImage.alt = image.alt;
  document.getElementById('viewer-caption').textContent = shots[shown].nextElementSibling.textContent;
}
shots.forEach((shot, index) => shot.addEventListener('click', event => {
  if (!viewer.showModal) return;
  event.preventDefault();
  showShot(index);
  sizeViewer();
  viewer.showModal();
}));
document.getElementById('viewer-previous').addEventListener('click', () => showShot(shown - 1));
document.getElementById('viewer-next').addEventListener('click', () => showShot(shown + 1));
document.getElementById('viewer-close').addEventListener('click', () => viewer.close());
viewer.addEventListener('click', event => { if (event.target === viewer) viewer.close(); });
viewer.addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft') showShot(shown - 1);
  else if (event.key === 'ArrowRight') showShot(shown + 1);
});
let swipe;
viewerImage.addEventListener('touchstart', event => { swipe = event.touches[0].clientX; }, {passive:true});
viewerImage.addEventListener('touchend', event => {
  const distance = event.changedTouches[0].clientX - swipe;
  if (Math.abs(distance) > 40) showShot(shown + (distance < 0 ? 1 : -1));
});
window.addEventListener('resize', () => { if (viewer.open) sizeViewer(); });
