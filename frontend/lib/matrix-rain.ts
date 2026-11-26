/**
 * Sannetic matrix rain.
 *
 * Port of vASanne/SanneticDesign `matrix/matrix-rain.js`, which itself comes
 * from vASanne/SanneticDashboard `public/scripts/matrix-rain.js` (d47716b).
 * Glyphs, gradient stops, frame rate, and device-pixel-ratio cap match that
 * module. The canvas stays transparent so the page background shows through.
 */

export const MATRIX_STOPS: readonly (readonly [number, number, number])[] = [
  [143, 209, 27],
  [28, 196, 160],
  [8, 194, 212],
];

/** 24 fps, same as the design-system module. */
export const MATRIX_FRAME_MS = 1000 / 24;

/** Device pixel ratio cap from the design-system module. */
export const MATRIX_MAX_DPR = 2;

export const MATRIX_GLYPHS = "01";

export interface MatrixHost {
  innerWidth: number;
  innerHeight: number;
  devicePixelRatio: number;
  document: Document;
  matchMedia(query: string): MediaQueryList;
  requestAnimationFrame(callback: FrameRequestCallback): number;
  cancelAnimationFrame(handle: number): void;
  setTimeout(handler: TimerHandler, timeout?: number): number;
  clearTimeout(timeoutId: number): void;
  addEventListener(type: string, listener: EventListener): void;
  removeEventListener(type: string, listener: EventListener): void;
}

interface Column {
  y: number;
  every: number;
  tick: number;
  active: boolean;
  last: string;
  trail: string;
  lead: string;
}

export function gradientRgb(t: number, towardWhite: number): string {
  const x = Math.max(0, Math.min(1, t)) * (MATRIX_STOPS.length - 1);
  const index = Math.min(MATRIX_STOPS.length - 2, x | 0);
  const f = x - index;
  const a = MATRIX_STOPS[index];
  const b = MATRIX_STOPS[index + 1];
  const channel = (i: number) => {
    const value = a[i] + (b[i] - a[i]) * f;
    return Math.round(value + (255 - value) * towardWhite);
  };
  return `rgb(${channel(0)},${channel(1)},${channel(2)})`;
}

export function capDevicePixelRatio(devicePixelRatio: number): number {
  const ratio = Number.isFinite(devicePixelRatio) && devicePixelRatio > 0 ? devicePixelRatio : 1;
  return Math.min(ratio, MATRIX_MAX_DPR);
}

/**
 * Draw the rain on `canvas` and return a cleanup function.
 * `prefers-reduced-motion: reduce` paints one static frame.
 * The loop pauses while the document is hidden.
 */
export function mountMatrixRain(canvas: HTMLCanvasElement, view: MatrixHost): () => void {
  const context = canvas.getContext("2d", { alpha: true });
  if (!context) {
    return () => undefined;
  }
  const ctx = context;

  const columns: Column[] = [];
  let fontSize = 16;
  let width = 0;
  let height = 0;
  let rafId = 0;
  let lastFrame = 0;
  let running = false;
  let cancelled = false;
  let resizeTimer = 0;

  const reducedQuery = view.matchMedia("(prefers-reduced-motion: reduce)");

  function glyph(): string {
    return MATRIX_GLYPHS.charAt((Math.random() * MATRIX_GLYPHS.length) | 0);
  }

  function font(): string {
    return `500 ${fontSize}px 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`;
  }

  function assignColors(): void {
    const count = columns.length;
    for (let i = 0; i < count; i += 1) {
      const t = count <= 1 ? 0 : i / (count - 1);
      columns[i].trail = gradientRgb(t, 0);
      columns[i].lead = gradientRgb(t, 0.62);
    }
  }

  function makeColumn(): Column {
    return {
      y: (Math.random() * (height / fontSize + 8)) | 0,
      every: 2 + ((Math.random() * 3) | 0),
      tick: (Math.random() * 4) | 0,
      active: Math.random() < 0.62,
      last: glyph(),
      trail: "",
      lead: "",
    };
  }

  function paintGlyph(ch: string, x: number, y: number, style: string, alpha: number): void {
    if (y < -fontSize || y > height) return;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = style;
    ctx.fillText(ch, x, y);
  }

  function seed(): void {
    ctx.clearRect(0, 0, width, height);
    ctx.font = font();
    ctx.textBaseline = "top";
    ctx.textAlign = "center";
    for (let i = 0; i < columns.length; i += 1) {
      const col = columns[i];
      if (!col.active) continue;
      const length = 6 + ((Math.random() * 12) | 0);
      const head = glyph();
      col.last = head;
      for (let t = length; t >= 1; t -= 1) {
        paintGlyph(
          glyph(),
          i * fontSize + fontSize / 2,
          (col.y - t) * fontSize,
          col.trail,
          Math.max(0.14, 0.78 * (1 - t / (length + 1))),
        );
      }
      paintGlyph(head, i * fontSize + fontSize / 2, col.y * fontSize, col.lead, 1);
    }
    ctx.globalAlpha = 1;
  }

  function paintStatic(): void {
    const rows = Math.ceil(height / fontSize);
    ctx.clearRect(0, 0, width, height);
    ctx.font = font();
    ctx.textBaseline = "top";
    ctx.textAlign = "center";
    for (let i = 0; i < columns.length; i += 2) {
      const col = columns[i];
      const length = 6 + ((Math.random() * 10) | 0);
      const start = (Math.random() * rows) | 0;
      for (let row = 0; row < length; row += 1) {
        paintGlyph(
          glyph(),
          i * fontSize + fontSize / 2,
          (start - row) * fontSize,
          row === 0 ? col.lead : col.trail,
          row === 0 ? 0.9 : Math.max(0.14, 0.7 - row * 0.05),
        );
      }
    }
    ctx.globalAlpha = 1;
  }

  function resize(): void {
    width = view.innerWidth || view.document.documentElement.clientWidth || 1;
    height = view.innerHeight || view.document.documentElement.clientHeight || 1;
    const dpr = capDevicePixelRatio(view.devicePixelRatio);
    fontSize = width < 700 ? 14 : 16;

    canvas.width = Math.max(1, Math.round(width * dpr));
    canvas.height = Math.max(1, Math.round(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = Math.max(1, Math.ceil(width / fontSize));
    columns.length = 0;
    for (let i = 0; i < count; i += 1) columns.push(makeColumn());
    assignColors();

    if (reducedQuery.matches) paintStatic();
    else seed();
  }

  function step(): void {
    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = "rgba(0, 0, 0, 0.11)";
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.font = font();
    ctx.textBaseline = "top";
    ctx.textAlign = "center";

    for (let i = 0; i < columns.length; i += 1) {
      const col = columns[i];
      if (!col.active) continue;
      const x = i * fontSize;
      col.tick += 1;
      if (col.tick >= col.every) {
        col.tick = 0;
        const prevY = (col.y - 1) * fontSize;
        if (prevY >= -fontSize && prevY <= height) {
          ctx.clearRect(x, prevY, fontSize, fontSize);
          ctx.fillStyle = col.trail;
          ctx.fillText(col.last, x + fontSize / 2, prevY);
        }
        col.y += 1;
        if (col.y * fontSize > height + fontSize * 2 && Math.random() > 0.35) {
          col.y = -((Math.random() * 16) | 0);
          col.every = 2 + ((Math.random() * 3) | 0);
        }
        col.last = glyph();
      }
      if (col.y * fontSize < height && col.y > -2) {
        const headY = col.y * fontSize;
        ctx.clearRect(x, headY, fontSize, fontSize);
        ctx.fillStyle = col.lead;
        ctx.fillText(col.last, x + fontSize / 2, headY);
      }
    }
  }

  function frame(now: number): void {
    if (!running) return;
    rafId = view.requestAnimationFrame(frame);
    if (view.document.hidden || reducedQuery.matches) return;
    if (now - lastFrame < MATRIX_FRAME_MS) return;
    lastFrame = now;
    step();
  }

  function start(): void {
    if (running || reducedQuery.matches || view.document.hidden) return;
    running = true;
    lastFrame = 0;
    rafId = view.requestAnimationFrame(frame);
  }

  function stop(): void {
    running = false;
    if (rafId) {
      view.cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  function onVisibility(): void {
    if (view.document.hidden) {
      stop();
      return;
    }
    start();
  }

  function onMotionChange(): void {
    stop();
    if (reducedQuery.matches) {
      paintStatic();
      return;
    }
    seed();
    start();
  }

  function onResize(): void {
    view.clearTimeout(resizeTimer);
    resizeTimer = view.setTimeout(resize, 120);
  }

  view.addEventListener("resize", onResize);
  view.document.addEventListener("visibilitychange", onVisibility);
  if (typeof reducedQuery.addEventListener === "function") {
    reducedQuery.addEventListener("change", onMotionChange);
  } else {
    const legacy = reducedQuery as MediaQueryList & {
      addListener?: (listener: () => void) => void;
    };
    legacy.addListener?.(onMotionChange);
  }

  function go(): void {
    if (cancelled) return;
    resize();
    start();
  }

  const fonts = view.document.fonts;
  if (fonts && typeof fonts.load === "function") {
    fonts.load(font()).then(go, go);
  } else {
    go();
  }

  return () => {
    cancelled = true;
    stop();
    view.clearTimeout(resizeTimer);
    view.removeEventListener("resize", onResize);
    view.document.removeEventListener("visibilitychange", onVisibility);
    if (typeof reducedQuery.removeEventListener === "function") {
      reducedQuery.removeEventListener("change", onMotionChange);
    } else {
      const legacy = reducedQuery as MediaQueryList & {
        removeListener?: (listener: () => void) => void;
      };
      legacy.removeListener?.(onMotionChange);
    }
  };
}
