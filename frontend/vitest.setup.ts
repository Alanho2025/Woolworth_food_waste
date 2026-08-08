import "@testing-library/jest-dom/vitest";

// jsdom implements neither of these, and both are used by the driver-route
// screen. Stubbing them here keeps the components under test honest — they
// still call the real API surface, they just get a no-op implementation.
if (!("speechSynthesis" in globalThis)) {
  Object.defineProperty(globalThis, "speechSynthesis", {
    writable: true,
    value: {
      getVoices: () => [],
      speak: () => undefined,
      cancel: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    },
  });
}

if (!("SpeechSynthesisUtterance" in globalThis)) {
  Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
    writable: true,
    value: class {
      text: string;
      lang = "en-NZ";
      rate = 1;
      constructor(text: string) {
        this.text = text;
      }
    },
  });
}

if (!("ResizeObserver" in globalThis)) {
  Object.defineProperty(globalThis, "ResizeObserver", {
    writable: true,
    value: class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    },
  });
}
