/**
 * DCLM Payroll - Professional Toast Notification System
 * Provides animated, auto-dismissable notifications across the app
 */
(function () {
  "use strict";

  // ── Configuration ──
  const DEFAULTS = {
    duration: 4000,
    position: "top-right",
    maxVisible: 5,
    animationDuration: 350,
    spacing: 12,
  };

  // ── State ──
  let container = null;
  let activeToasts = [];
  let idCounter = 0;
  let isPaused = false;

  // ── Icons ──
  const ICONS = {
    success: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  };

  const COLORS = {
    success: { bg: "#ecfdf5", border: "#a7f3d0", text: "#065f46", icon: "#10b981" },
    error: { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", icon: "#ef4444" },
    warning: { bg: "#fffbeb", border: "#fde68a", text: "#92400e", icon: "#f59e0b" },
    info: { bg: "#eff6ff", border: "#bfdbfe", text: "#1e40af", icon: "#3b82f6" },
  };

  // ── Toast Manager ──
  function getContainer() {
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 100000;
        display: flex;
        flex-direction: column;
        gap: ${DEFAULTS.spacing}px;
        pointer-events: none;
        max-width: 400px;
        width: calc(100% - 40px);
      `;
      document.body.appendChild(container);
    }
    return container;
  }

  function removeToast(id) {
    const index = activeToasts.findIndex((t) => t.id === id);
    if (index === -1) return;
    const toast = activeToasts[index];
    const el = toast.element;

    // Slide and fade out
    el.style.transform = "translateX(120%)";
    el.style.opacity = "0";
    el.style.maxHeight = "0";
    el.style.marginBottom = "0";
    el.style.padding = "0 16px";

    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el);
      activeToasts.splice(index, 1);
      repositionToasts();
    }, DEFAULTS.animationDuration);
  }

  function repositionToasts() {
    const items = container.querySelectorAll(".toast-item");
    items.forEach((el, i) => {
      el.style.zIndex = items.length - i;
    });
  }

  function createToast(type, title, message, opts) {
    const config = Object.assign({}, DEFAULTS, opts);
    const colors = COLORS[type] || COLORS.info;
    const icon = ICONS[type] || ICONS.info;
    const id = ++idCounter;

    const el = document.createElement("div");
    el.className = "toast-item";
    el.dataset.id = id;
    el.style.cssText = `
      pointer-events: all;
      background: ${colors.bg};
      border: 1px solid ${colors.border};
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
      display: flex;
      gap: 12px;
      align-items: flex-start;
      transform: translateX(120%);
      opacity: 0;
      transition: all ${DEFAULTS.animationDuration}ms cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
      overflow: hidden;
      max-height: 300px;
    `;

    // Icon
    const iconWrap = document.createElement("div");
    iconWrap.style.cssText = `
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      color: ${colors.icon};
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 1px;
    `;
    iconWrap.innerHTML = icon;
    el.appendChild(iconWrap);

    // Content
    const content = document.createElement("div");
    content.style.cssText = "flex: 1; min-width: 0;";
    
    const titleEl = document.createElement("div");
    titleEl.style.cssText = `
      font-weight: 700;
      font-size: 0.88rem;
      color: ${colors.text};
      margin-bottom: 2px;
      font-family: 'Inter', -apple-system, sans-serif;
    `;
    titleEl.textContent = title;
    content.appendChild(titleEl);

    if (message) {
      const msgEl = document.createElement("div");
      msgEl.style.cssText = `
        font-size: 0.82rem;
        color: ${colors.text};
        opacity: 0.85;
        line-height: 1.4;
        font-family: 'Inter', -apple-system, sans-serif;
        word-break: break-word;
      `;
      msgEl.textContent = message;
      content.appendChild(msgEl);
    }

    el.appendChild(content);

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${colors.text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
    closeBtn.style.cssText = `
      flex-shrink: 0;
      background: none;
      border: none;
      cursor: pointer;
      padding: 2px;
      opacity: 0.4;
      transition: opacity 0.2s ease;
      margin-left: 4px;
    `;
    closeBtn.onmouseenter = () => (closeBtn.style.opacity = "0.8");
    closeBtn.onmouseleave = () => (closeBtn.style.opacity = "0.4");
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      removeToast(id);
    };
    el.appendChild(closeBtn);

    // Progress bar
    if (type !== "error" && config.duration > 0) {
      const progressBar = document.createElement("div");
      progressBar.style.cssText = `
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        background: ${colors.icon};
        opacity: 0.25;
        border-radius: 0 2px 0 0;
        width: 100%;
        transition: width ${config.duration}ms linear;
      `;
      el.appendChild(progressBar);
      
      // Start progress animation after show
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          progressBar.style.width = "0%";
        });
      });
    }

    // Ensure max visible
    const toastContainer = getContainer();
    while (activeToasts.length >= config.maxVisible) {
      removeToast(activeToasts[0].id);
    }

    // Add to DOM
    container.appendChild(el);
    activeToasts.push({ id, element: el });

    // Animate in
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.transform = "translateX(0)";
        el.style.opacity = "1";
      });
    });

    // Auto dismiss
    if (config.duration > 0) {
      setTimeout(() => {
        if (!isPaused) removeToast(id);
      }, config.duration + DEFAULTS.animationDuration);
    }

    return {
      id,
      close: () => removeToast(id),
      element: el,
    };
  }

  // ── Public API ──
  window.DCLMToast = {
    success: (title, message, opts) => createToast("success", title, message, opts),
    error: (title, message, opts) => createToast("error", title, message, opts),
    warning: (title, message, opts) => createToast("warning", title, message, opts),
    info: (title, message, opts) => createToast("info", title, message, opts),
  };

  // ── Auto-initialize from flash messages ──
  document.addEventListener("DOMContentLoaded", function () {
    try {
      const flash = localStorage.getItem("dclm_flash");
      if (flash) {
        const data = JSON.parse(flash);
        if (data.type && data.title) {
          setTimeout(() => {
            DCLMToast[data.type](data.title, data.message || "", {
              duration: data.duration || 5000,
            });
          }, 300);
        }
        localStorage.removeItem("dclm_flash");
      }
    } catch (e) {}

    // Check for flash meta tags
    const flashMeta = document.querySelector('meta[name="flash-message"]');
    if (flashMeta) {
      try {
        const data = JSON.parse(flashMeta.content);
        if (data.type && data.title) {
          setTimeout(() => {
            DCLMToast[data.type](data.title, data.message || "", {
              duration: data.duration || 5000,
            });
          }, 500);
        }
      } catch (e) {}
    }
  });
})();
