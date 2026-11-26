import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  MATRIX_FRAME_MS,
  MATRIX_MAX_DPR,
  capDevicePixelRatio,
  gradientRgb,
  mountMatrixRain,
  type MatrixHost,
} from "./matrix-rain.ts";

const root = fileURLToPath(new URL("..", import.meta.url));

test("brand gradient matches the logo stops", () => {
  assert.equal(gradientRgb(0, 0), "rgb(143,209,27)");
  assert.equal(gradientRgb(0.5, 0), "rgb(28,196,160)");
  assert.equal(gradientRgb(1, 0), "rgb(8,194,212)");
  assert.equal(gradientRgb(0, 1), "rgb(255,255,255)");
  assert.equal(MATRIX_FRAME_MS, 1000 / 24);
  assert.equal(MATRIX_MAX_DPR, 2);
  assert.equal(capDevicePixelRatio(4), 2);
  assert.equal(capDevicePixelRatio(Number.NaN), 1);
});

test("stylesheet keeps the design opacity and does not use inline styles", () => {
  const css = readFileSync(join(root, "styles/matrix-rain.css"), "utf8");
  const component = readFileSync(join(root, "components/matrix-rain.tsx"), "utf8");
  assert.match(css, /opacity:\s*0\.78/);
  assert.match(css, /opacity:\s*0\.35/);
  assert.match(css, /pointer-events:\s*none/);
  assert.match(css, /position:\s*fixed/);
  assert.match(component, /aria-hidden="true"/);
  assert.equal(component.includes("style="), false);
  assert.equal(component.includes("unsafe-inline"), false);
});

test("reduced motion paints one static frame and does not schedule frames", () => {
  const drawn: string[] = [];
  const { canvas, host, frames } = fakeHost({ reduced: true });
  const ctx = canvas.getContext("2d") as FakeContext;
  ctx.onFillText = (ch) => drawn.push(ch);
  const stop = mountMatrixRain(canvas, host);
  assert.equal(frames.length, 0);
  assert.ok(drawn.length > 0);
  assert.ok(drawn.every((ch) => ch === "0" || ch === "1"));
  stop();
  assert.equal(listenerCount(host), 0);
});

test("a hidden document does not start the loop", () => {
  const { canvas, host, frames } = fakeHost({ hidden: true });
  const stop = mountMatrixRain(canvas, host);
  assert.equal(frames.length, 0);
  stop();
});

test("animation is capped at 24 fps and stops on cleanup", () => {
  const { canvas, host, frames } = fakeHost({});
  const ctx = canvas.getContext("2d") as FakeContext;
  let eroded = 0;
  ctx.onFillRect = () => {
    eroded += 1;
  };
  const stop = mountMatrixRain(canvas, host);
  assert.equal(canvas.width, 64);
  assert.equal(frames.length, 1);
  frames[0](1000);
  assert.equal(eroded, 1);
  frames[1](1000 + MATRIX_FRAME_MS - 1);
  assert.equal(eroded, 1);
  frames[2](1000 + MATRIX_FRAME_MS);
  assert.equal(eroded, 2);
  stop();
  assert.equal(listenerCount(host), 0);
  const scheduled = frames.length;
  frames[frames.length - 1](1000);
  assert.equal(frames.length, scheduled);
});

test("resize waits 120ms and caps the device pixel ratio", () => {
  const { canvas, host } = fakeHost({ dpr: 3, width: 800, height: 600 });
  const stop = mountMatrixRain(canvas, host);
  assert.equal(canvas.width, 1600);
  host.innerWidth = 400;
  host.dispatch("resize");
  assert.equal(canvas.width, 1600);
  host.flushTimer();
  assert.equal(canvas.width, 800);
  stop();
});

interface FakeContext extends CanvasRenderingContext2D {
  onFillText: (ch: string) => void;
  onFillRect: () => void;
}

function listenerCount(host: { listeners: Map<string, Set<EventListener>>; document: { listeners?: Map<string, Set<EventListener>> } }): number {
  const sets = [...host.listeners.values(), ...(host.document.listeners?.values() ?? [])];
  return sets.reduce((sum, set) => sum + set.size, 0);
}

function fakeHost(options: { reduced?: boolean; hidden?: boolean; dpr?: number; width?: number; height?: number }): {
  canvas: HTMLCanvasElement;
  host: MatrixHost & { listeners: Map<string, Set<EventListener>>; dispatch: (type: string) => void; flushTimer: () => void };
  frames: Array<(now: number) => void>;
} {
  const frames: Array<(now: number) => void> = [];
  const listeners = new Map<string, Set<EventListener>>();
  const docListeners = new Map<string, Set<EventListener>>();
  const mediaListeners = new Set<() => void>();
  let timer: (() => void) | null = null;
  let nextId = 1;
  const width = options.width ?? 64;
  const height = options.height ?? 48;

  const context = {
    setTransform() {},
    clearRect() {},
    fillRect() {
      context.onFillRect();
    },
    fillText(text: string) {
      context.onFillText(text);
    },
    font: "",
    textBaseline: "top" as CanvasTextBaseline,
    textAlign: "center" as CanvasTextAlign,
    fillStyle: "",
    globalAlpha: 1,
    globalCompositeOperation: "source-over",
    onFillText(_ch: string) {},
    onFillRect() {},
  };

  const canvas = {
    width: 1,
    height: 1,
    getContext() {
      return context;
    },
  } as unknown as HTMLCanvasElement;

  const media = {
    matches: options.reduced === true,
    media: "(prefers-reduced-motion: reduce)",
    addEventListener(_type: string, listener: EventListener) {
      mediaListeners.add(listener as () => void);
    },
    removeEventListener(_type: string, listener: EventListener) {
      mediaListeners.delete(listener as () => void);
    },
    dispatchEvent() {
      return true;
    },
    onchange: null,
    addListener(listener: () => void) {
      mediaListeners.add(listener);
    },
    removeListener(listener: () => void) {
      mediaListeners.delete(listener);
    },
  } as MediaQueryList;

  const doc = {
    hidden: options.hidden === true,
    documentElement: { clientWidth: width, clientHeight: height },
    addEventListener(type: string, listener: EventListener) {
      const set = docListeners.get(type) ?? new Set();
      set.add(listener);
      docListeners.set(type, set);
    },
    removeEventListener(type: string, listener: EventListener) {
      docListeners.get(type)?.delete(listener);
    },
    listeners: docListeners,
  };

  const host = {
    innerWidth: width,
    innerHeight: height,
    devicePixelRatio: options.dpr ?? 1,
    document: doc as unknown as Document,
    matchMedia() {
      return media;
    },
    requestAnimationFrame(callback: FrameRequestCallback) {
      frames.push(callback);
      nextId += 1;
      return nextId;
    },
    cancelAnimationFrame() {},
    setTimeout(handler: TimerHandler) {
      timer = typeof handler === "function" ? handler : null;
      return 1;
    },
    clearTimeout() {
      timer = null;
    },
    addEventListener(type: string, listener: EventListener) {
      const set = listeners.get(type) ?? new Set();
      set.add(listener);
      listeners.set(type, set);
    },
    removeEventListener(type: string, listener: EventListener) {
      listeners.get(type)?.delete(listener);
    },
    listeners,
    dispatch(type: string) {
      for (const listener of listeners.get(type) ?? []) listener(new Event(type));
    },
    flushTimer() {
      const run = timer;
      timer = null;
      run?.();
    },
  };

  return { canvas, host, frames };
}
