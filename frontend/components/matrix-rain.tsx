"use client";

import { useEffect, useRef } from "react";

import { mountMatrixRain, type MatrixHost } from "@/lib/matrix-rain";

function browserMatrixHost(): MatrixHost {
  return {
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
    document,
    matchMedia: (query) => window.matchMedia(query),
    requestAnimationFrame: (callback) => window.requestAnimationFrame(callback),
    cancelAnimationFrame: (handle) => window.cancelAnimationFrame(handle),
    setTimeout: (handler, timeout) => window.setTimeout(handler, timeout),
    clearTimeout: (timeoutId) => window.clearTimeout(timeoutId),
    addEventListener: (type, listener) => window.addEventListener(type, listener),
    removeEventListener: (type, listener) => window.removeEventListener(type, listener),
  };
}

/** Full-viewport matrix rain. Decorative only; the stylesheet positions it. */
export function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    return mountMatrixRain(canvas, browserMatrixHost());
  }, []);

  return <canvas ref={canvasRef} id="matrix-rain" className="matrix-rain" width={1} height={1} aria-hidden="true" />;
}
