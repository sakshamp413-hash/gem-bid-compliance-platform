import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";

afterEach(cleanup);

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!("ResizeObserver" in globalThis)) {
  (globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverStub;
}

// jsdom has no layout: give SVG measurements a sane default
Object.defineProperty(globalThis.SVGElement.prototype, "getBBox", {
  writable: true,
  value: () => ({ x: 0, y: 0, width: 160, height: 160 }),
});