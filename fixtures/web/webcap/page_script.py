"""The script every capture page runs before its own: storage, WebSocket counting, animation
seeking and a caret drawn on the virtual clock (see webcap.director)."""

INIT_SCRIPT = r"""
(() => {
  // the project's LOCAL_STORAGE (theme and similar settings), set before the app reads it
  try {
    for (const [key, value] of Object.entries(__STORAGE__)) {
      localStorage.setItem(key, JSON.stringify(value));
    }
  } catch (_) {}
  // Headless reports notifications as blocked whatever the grant; show the
  // ordinary "off" switch a desktop browser shows instead of that warning.
  if (window.Notification) {
    Object.defineProperty(Notification, "permission", { get: () => "granted" });
  }
  window.__rx = 0;
  const Native = window.WebSocket;
  class Counted extends Native {
    constructor(...args) {
      super(...args);
      this.addEventListener("message", () => { window.__rx += 1; });
    }
  }
  window.WebSocket = Counted;
  const births = new WeakMap();
  window.__syncAnimations = () => {
    const now = performance.now();
    for (const a of document.getAnimations()) {
      let born = births.get(a);
      if (born === undefined) { born = now; births.set(a, born); }
      const local = (now - born) * (a.playbackRate || 1);
      const end = a.effect ? a.effect.getComputedTiming().endTime : Infinity;
      if (Number.isFinite(end) && local >= end) {
        if (a.playState !== "finished") a.finish();
        continue;
      }
      if (a.playState !== "paused") a.pause();
      a.currentTime = local;
    }
  };
  // The native caret blinks on a real-time timer, which frame stepping turns
  // into flicker. Hide it and draw one on the virtual clock: solid for 500 ms
  // after focus or input, then 500 ms on / 500 ms off, as Chrome does.
  const caret = document.createElement("div");
  caret.style.cssText = "position:fixed;width:1px;pointer-events:none;z-index:2147483647;display:none";
  const measure = document.createElement("canvas").getContext("2d");
  let typedAt = 0;
  const stamp = () => { typedAt = performance.now(); };
  document.addEventListener("input", stamp, true);
  document.addEventListener("focusin", stamp, true);
  const TEXT = new Set(["text", "search", "email", "url", ""]);
  window.__drawCaret = () => {
    const el = document.activeElement;
    if (!(el instanceof HTMLInputElement) || !TEXT.has(el.type) || el.selectionStart !== el.selectionEnd) {
      caret.style.display = "none";
      return;
    }
    if (!caret.isConnected) document.body.appendChild(caret);
    const cs = getComputedStyle(el);
    // cs.font is empty when the font shorthand cannot express the computed
    // style, so assemble it.
    measure.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    measure.letterSpacing = cs.letterSpacing;
    const rect = el.getBoundingClientRect();
    const size = parseFloat(cs.fontSize);
    const height = Math.round(size * 1.2);
    const x = rect.left + parseFloat(cs.borderLeftWidth) + parseFloat(cs.paddingLeft)
      + measure.measureText(el.value.slice(0, el.selectionStart)).width - el.scrollLeft;
    const on = (performance.now() - typedAt) % 1000 < 500;
    caret.style.display = on ? "block" : "none";
    caret.style.left = `${x}px`;
    caret.style.top = `${rect.top + (rect.height - height) / 2}px`;
    caret.style.height = `${height}px`;
    caret.style.background = cs.color;
  };
  window.__frame = () => { window.__syncAnimations(); window.__drawCaret(); };
  const hide = () => {
    const style = document.createElement("style");
    style.textContent = "*{scrollbar-width:none!important}*::-webkit-scrollbar{display:none!important}" +
      ".xterm .scrollbar{opacity:0!important}input{caret-color:transparent!important}";
    document.head.appendChild(style);
  };
  if (document.head) hide(); else document.addEventListener("DOMContentLoaded", hide);
})();
"""
