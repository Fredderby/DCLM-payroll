/**
 * DCLM Payroll - Professional Progress & Loading System
 * Manages global loading states, progress bars, and processing overlays
 */
(function () {
  "use strict";

  // ── Configuration ──
  const PROGRESS_DEFAULTS = {
    overlay: true,
    showPercentage: true,
    showMessage: true,
    canCancel: false,
    minDisplayTime: 800,
  };

  // ── State ──
  let activeProgress = null;
  let progressIdCounter = 0;

  // ── Global Loading Overlay ──
  function showLoading(message) {
    let overlay = document.getElementById("global-loading-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "global-loading-overlay";
      overlay.style.cssText = `
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.35);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        z-index: 50000;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.25s ease;
      `;
      
      const card = document.createElement("div");
      card.style.cssText = `
        background: #fff;
        border-radius: 20px;
        padding: 2rem 2.5rem;
        max-width: 420px;
        width: 90%;
        box-shadow: 0 25px 60px rgba(0,0,0,0.2);
        text-align: center;
      `;

      // Spinner
      const spinner = document.createElement("div");
      spinner.style.cssText = `
        width: 48px; height: 48px;
        border: 4px solid #e0e7ff;
        border-top-color: #1a365d;
        border-radius: 50%;
        animation: dclmSpin 0.7s linear infinite;
        margin: 0 auto 1rem;
      `;
      card.appendChild(spinner);

      // Message
      const msgEl = document.createElement("div");
      msgEl.id = "loading-message";
      msgEl.style.cssText = `
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 0.92rem;
        font-weight: 600;
        color: #1a1a2e;
      `;
      msgEl.textContent = message || "Loading...";
      card.appendChild(msgEl);

      overlay.appendChild(card);

      // Inject keyframe animation
      if (!document.getElementById("dclm-spin-style")) {
        const style = document.createElement("style");
        style.id = "dclm-spin-style";
        style.textContent = `@keyframes dclmSpin { to { transform: rotate(360deg); } }`;
        document.head.appendChild(style);
      }

      document.body.appendChild(overlay);
    }

    const msgEl = document.getElementById("loading-message");
    if (msgEl) msgEl.textContent = message || "Loading...";

    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
    });

    return {
      close: () => {
        overlay.style.opacity = "0";
        setTimeout(() => {
          if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        }, 300);
      },
      setMessage: (m) => {
        const e = document.getElementById("loading-message");
        if (e) e.textContent = m;
      },
    };
  }

  // ── Progress Overlay ──
  function showProgress(opts) {
    const config = Object.assign({}, PROGRESS_DEFAULTS, opts);
    const id = ++progressIdCounter;

    // Close existing
    if (activeProgress) {
      activeProgress.close();
    }

    const overlay = document.createElement("div");
    overlay.className = "dclm-progress-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.45);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      z-index: 99000;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.25s ease;
    `;

    const card = document.createElement("div");
    card.style.cssText = `
      background: #fff;
      border-radius: 20px;
      padding: 2rem 2.5rem;
      max-width: 480px;
      width: 90%;
      box-shadow: 0 25px 60px rgba(0,0,0,0.2);
      text-align: center;
    `;

    // Title
    const titleEl = document.createElement("div");
    titleEl.style.cssText = `
      font-family: 'Inter', -apple-system, sans-serif;
      font-size: 1rem;
      font-weight: 700;
      color: #1a1a2e;
      margin-bottom: 0.5rem;
    `;
    titleEl.textContent = config.title || "Processing...";
    card.appendChild(titleEl);

    // Progress bar container
    const barContainer = document.createElement("div");
    barContainer.style.cssText = `
      width: 100%;
      height: 8px;
      background: #e5e7eb;
      border-radius: 4px;
      overflow: hidden;
      margin: 1.25rem 0 0.5rem;
    `;

    const barFill = document.createElement("div");
    barFill.style.cssText = `
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #1a365d, #3b82f6);
      border-radius: 4px;
      transition: width 0.3s ease;
    `;
    barContainer.appendChild(barFill);
    card.appendChild(barContainer);

    // Percentage
    const pctEl = document.createElement("div");
    pctEl.style.cssText = `
      font-family: 'Inter', -apple-system, sans-serif;
      font-size: 0.85rem;
      font-weight: 700;
      color: #1a365d;
      margin-bottom: 0.25rem;
    `;
    pctEl.textContent = "0%";
    card.appendChild(pctEl);

    // Message
    const msgEl = document.createElement("div");
    msgEl.id = "dclm-progress-msg";
    msgEl.style.cssText = `
      font-family: 'Inter', -apple-system, sans-serif;
      font-size: 0.82rem;
      color: #666;
      margin-bottom: 0.5rem;
      line-height: 1.4;
    `;
    msgEl.textContent = config.message || "";
    card.appendChild(msgEl);

    // Cancel button
    if (config.canCancel) {
      const cancelBtn = document.createElement("button");
      cancelBtn.textContent = "Cancel";
      cancelBtn.style.cssText = `
        margin-top: 0.75rem;
        padding: 0.5rem 1.5rem;
        border-radius: 10px;
        border: 1.5px solid #d1d5db;
        background: #fff;
        color: #666;
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        font-family: 'Inter', -apple-system, sans-serif;
        transition: all 0.2s ease;
      `;
      cancelBtn.onmouseenter = () => {
        cancelBtn.style.borderColor = "#ef4444";
        cancelBtn.style.color = "#ef4444";
      };
      cancelBtn.onmouseleave = () => {
        cancelBtn.style.borderColor = "#d1d5db";
        cancelBtn.style.color = "#666";
      };
      cancelBtn.onclick = () => {
        if (config.onCancel) config.onCancel();
        overlay.style.opacity = "0";
        setTimeout(() => {
          if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        }, 300);
      };
      card.appendChild(cancelBtn);
    }

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
    });

    const startTime = Date.now();

    const instance = {
      id,
      close: () => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, PROGRESS_DEFAULTS.minDisplayTime - elapsed);
        
        setTimeout(() => {
          overlay.style.opacity = "0";
          setTimeout(() => {
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
            if (activeProgress && activeProgress.id === id) {
              activeProgress = null;
            }
          }, 300);
        }, remaining);
      },
      setProgress: (pct, message) => {
        if (typeof pct === "number") {
          const clamped = Math.max(0, Math.min(100, pct));
          barFill.style.width = `${clamped}%`;
          pctEl.textContent = `${Math.round(clamped)}%`;
        }
        if (message) {
          msgEl.textContent = message;
        }
      },
      setMessage: (msg) => {
        msgEl.textContent = msg;
      },
      complete: (message) => {
        barFill.style.width = "100%";
        pctEl.textContent = "100%";
        if (message) msgEl.textContent = message;
        
        setTimeout(() => {
          instance.close();
        }, 1200);
      },
    };

    // Simulate progress if not manually updated (prevents stuck 0%)
    if (!opts || !opts.preventAuto) {
      let autoPct = 0;
      const autoInterval = setInterval(() => {
        if (autoPct >= 90) {
          clearInterval(autoInterval);
          return;
        }
        // Slow down as progress increases
        const increment = Math.max(0.5, (90 - autoPct) * 0.08);
        autoPct = Math.min(90, autoPct + increment);
        barFill.style.width = `${autoPct}%`;
        pctEl.textContent = `${Math.round(autoPct)}%`;
      }, 500);

      // Store reference to clear
      instance._autoInterval = autoInterval;
    }

    activeProgress = instance;
    return instance;
  }

  // ── Inline Progress Bar ──
  function createInlineProgress(containerEl, opts) {
    const config = Object.assign(
      {
        height: 6,
        color: "linear-gradient(90deg, #1a365d, #3b82f6)",
        showPercentage: true,
        initialMessage: "",
      },
      opts
    );

    const wrapper = document.createElement("div");
    wrapper.style.cssText = `
      width: 100%;
      margin: 0.5rem 0;
    `;

    const barContainer = document.createElement("div");
    barContainer.style.cssText = `
      width: 100%;
      height: ${config.height}px;
      background: #e5e7eb;
      border-radius: ${config.height / 2}px;
      overflow: hidden;
    `;

    const barFill = document.createElement("div");
    barFill.style.cssText = `
      height: 100%;
      width: 0%;
      background: ${config.color};
      border-radius: ${config.height / 2}px;
      transition: width 0.3s ease;
    `;
    barContainer.appendChild(barFill);
    wrapper.appendChild(barContainer);

    if (config.showPercentage) {
      const pctEl = document.createElement("div");
      pctEl.style.cssText = `
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 0.78rem;
        font-weight: 600;
        color: #1a365d;
        margin-top: 4px;
      `;
      pctEl.textContent = "0%";
      wrapper.appendChild(pctEl);
    }

    if (config.initialMessage) {
      const msgEl = document.createElement("div");
      msgEl.style.cssText = `
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 0.78rem;
        color: #666;
        margin-top: 2px;
      `;
      msgEl.textContent = config.initialMessage;
      wrapper.appendChild(msgEl);
    }

    containerEl.appendChild(wrapper);

    return {
      setProgress: (pct, message) => {
        const clamped = Math.max(0, Math.min(100, pct));
        barFill.style.width = `${clamped}%`;
        if (config.showPercentage) {
          pctEl.textContent = `${Math.round(clamped)}%`;
        }
        if (message && msgEl) msgEl.textContent = message;
      },
      complete: (message) => {
        barFill.style.width = "100%";
        if (config.showPercentage) pctEl.textContent = "100%";
        if (message && msgEl) msgEl.textContent = message;
      },
      element: wrapper,
    };
  }

  // ── Button Loading State ──
  function setButtonLoading(btn, isLoading, text) {
    if (!btn) return;
    
    if (isLoading) {
      btn._originalHTML = btn.innerHTML;
      btn._originalDisabled = btn.disabled;
      btn.disabled = true;
      btn.innerHTML = `<span class="dclm-btn-spinner" style="display:inline-flex;align-items:center;gap:8px"><span style="display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:dclmSpin 0.6s linear infinite"></span>${text || "Processing..."}</span>`;
    } else {
      btn.disabled = btn._originalDisabled || false;
      btn.innerHTML = btn._originalHTML || btn.innerHTML;
    }
  }

  // ── Duplicate Action Prevention ──
  const actionLocks = {};

  function lockAction(key) {
    if (actionLocks[key]) return false;
    actionLocks[key] = true;
    return true;
  }

  function unlockAction(key) {
    delete actionLocks[key];
  }

  function isActionLocked(key) {
    return !!actionLocks[key];
  }

  // ── Auto-attach to forms ──
  document.addEventListener("DOMContentLoaded", function () {
    // Add loading state to all form submissions
    document.addEventListener("submit", function (e) {
      const form = e.target;
      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn) {
        setTimeout(() => {
          setButtonLoading(submitBtn, true, "Processing...");
        }, 50);
      }
    });

    // Auto-disable submit buttons on click (prevents double submits)
    document.addEventListener("click", function (e) {
      const btn = e.target.closest('[type="submit"]');
      if (btn && btn.form) {
        setTimeout(() => {
          btn.disabled = true;
        }, 10);
      }
    });
  });

  // ── Public API ──
  window.DCLMProgress = {
    showLoading,
    showProgress,
    createInlineProgress,
    setButtonLoading,
    lockAction,
    unlockAction,
    isActionLocked,
  };
})();
