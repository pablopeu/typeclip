// TypeClip — content.js
// Se inyecta SOLO al invocar la extensión (chrome.scripting + activeTab).
// Tres funciones:
//   1. init:          reporta si el elemento con foco (este frame) es editable.
//   2. monitores:     Esc (cancelar) y cambio de document.activeElement → abort.
//   3. exec-type:     jugador de FALLBACK 1/2: eventos KeyboardEvent sintéticos
//                     + beforeinput + execCommand("insertText") de UN code point
//                     (o setter nativo si execCommand falla) + input + keyup.
//
// IMPORTANTE (regla A): nunca más de UN code point por evento de input, nunca
// eventos "paste", nunca DataTransfer. Los inputTypes que genera este archivo
// son únicamente insertText, insertLineBreak/insertParagraph y deleteContentBackward.
// Estos eventos son isTrusted=false; con el método principal (CDP) son true.

if (!window.__typeclip) {
  window.__typeclip = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---- Elemento con foco, atravesando shadow DOM abiertos -------------------
  function deepActiveElement(doc = document) {
    let el = doc.activeElement;
    while (el && el.shadowRoot && el.shadowRoot.activeElement) {
      el = el.shadowRoot.activeElement;
    }
    return el;
  }

  const TEXT_INPUT_TYPES = new Set(["text", "search", "tel", "url", "email", "password", "number", ""]);
  // NOTA: cada frame solo examina SU document.activeElement. Con inyección
  // allFrames, el frame que tiene el editable enfocado es el que responde ok.
  function editableRoot() {
    const el = deepActiveElement();
    if (!el) return null;
    const tag = el.tagName;
    if (tag === "TEXTAREA") return el.readOnly || el.disabled ? null : el;
    if (tag === "INPUT") {
      if (el.readOnly || el.disabled) return null;
      return TEXT_INPUT_TYPES.has((el.type || "").toLowerCase()) ? el : null;
    }
    if (el.isContentEditable) return el;
    return null;
  }

  // ---- Lectura del campo (para la verificación final) ------------------------
  function fieldText(el) {
    if (!el) return "";
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") return el.value ?? "";
    return el.innerText ?? el.textContent ?? "";
  }

  // ---- Eventos sintéticos (solo para el fallback; isTrusted=false) ----------
  function fireKey(target, type, k) {
    target.dispatchEvent(new KeyboardEvent(type, {
      key: k.key, code: k.code || "", keyCode: k.keyCode || 0, which: k.keyCode || 0,
      shiftKey: !!k.shift, ctrlKey: false, altKey: false, metaKey: false,
      bubbles: true, cancelable: true, composed: true,
    }));
  }
  function fireInputEvent(target, type, data, inputType) {
    try {
      target.dispatchEvent(new InputEvent(type, {
        inputType, data: data === undefined ? null : data,
        bubbles: true, cancelable: true, composed: true,
      }));
    } catch (_) { /* InputEvent muy viejo: omitir, execCommand igual dispara input */ }
  }

  // ---- Inserción por setter nativo (FALLBACK 2) ------------------------------
  // Un solo code point por llamada. Dispara "input" manualmente porque el
  // setter nativo NO dispara eventos (justamente por eso lo usamos).
  function insertViaSetter(el, ch) {
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      const start = el.selectionStart ?? el.value.length;
      const end = el.selectionEnd ?? start;
      const v = el.value;
      (setter ? setter.call(el, v.slice(0, start) + ch + v.slice(end)) : (el.value = v.slice(0, start) + ch + v.slice(end)));
      const pos = start + Array.from(ch).length; // por si ch fuera >1 cp (no debería)
      try { el.setSelectionRange(pos, pos); } catch (_) {}
      return true;
    }
    // contenteditable: insertar en el caret con Range
    const doc = el.ownerDocument;
    const sel = doc.getSelection();
    if (!sel || !sel.rangeCount) return false;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    const node = doc.createTextNode(ch);
    range.insertNode(node);
    range.setStartAfter(node);
    range.setEndAfter(node);
    sel.removeAllRanges();
    sel.addRange(range);
    return true;
  }

  function deleteAtCaret(el) {
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      const v = el.value;
      if (el.selectionStart != null && el.selectionStart === el.selectionEnd && el.selectionStart > 0) {
        const p = el.selectionStart;
        setter ? setter.call(el, v.slice(0, p - 1) + v.slice(p)) : (el.value = v.slice(0, p - 1) + v.slice(p));
        try { el.setSelectionRange(p - 1, p - 1); } catch (_) {}
      }
      return;
    }
    const doc = el.ownerDocument;
    const sel = doc.getSelection();
    if (!sel || !sel.rangeCount) return;
    const range = sel.getRangeAt(0).cloneRange();
    if (range.collapsed) range.setStart(range.startContainer, Math.max(0, range.startOffset - 1));
    range.deleteContents();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  // ---- Humanización: MISMA LÓGICA que background.js (mantener sincronizado) --
  function makeHumanizer(cfg) {
    const base = 60000 / (Math.max(10, cfg.wpm) * 5);
    const s = Math.max(0.05, cfg.jitter / 100);
    let spare = null;
    function gauss() {
      if (spare !== null) { const v = spare; spare = null; return v; }
      let u = 0, v = 0;
      while (u === 0) u = Math.random();
      while (v === 0) v = Math.random();
      const r = Math.sqrt(-2 * Math.log(u));
      spare = r * Math.sin(2 * Math.PI * v);
      return r * Math.cos(2 * Math.PI * v);
    }
    return function delay(prevCh) {
      let d = Math.exp(Math.log(base) - (s * s) / 2 + s * gauss());
      d = Math.min(Math.max(d, base * 0.25), base * 4);
      if (cfg.pauses && prevCh) {
        if (prevCh === "\n") d *= 4 + Math.random() * 4;
        else if (prevCh === " ") d *= 1.8 + Math.random() * 1.2;
        else if (".;:!?".includes(prevCh)) d *= 2.5 + Math.random() * 2.5;
        else if (prevCh === ",") d *= 2 + Math.random() * 1.5;
      }
      if (Math.random() * 100 < cfg.thinkPct) d += 500 + Math.random() * 1000;
      return d;
    };
  }

  // ---- Estado del monitor ----------------------------------------------------
  let monitoredRoot = null;
  let monitorCleanup = null;
  let stopTyping = null; // función para cortar el loop de exec-type

  function startMonitor() {
    stopMonitor();
    monitoredRoot = editableRoot();
    const onKey = (e) => {
      // Solo Esc REAL del usuario (isTrusted=true) cancela el tipeo.
      if (e.isTrusted && e.key === "Escape") {
        try { chrome.runtime.sendMessage({ tc: "esc" }).catch?.(() => {}); } catch (_) {}
      }
    };
    const onFocusMove = () => {
      // focusin/focusout: al próximo tick el foco ya se asentó.
      setTimeout(() => {
        const cur = editableRoot();
        if (monitoredRoot !== null && cur !== monitoredRoot) {
          try { chrome.runtime.sendMessage({ tc: "editable-changed" }).catch?.(() => {}); } catch (_) {}
        }
      }, 0);
    };
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("focusin", onFocusMove, true);
    document.addEventListener("focusout", onFocusMove, true);
    monitorCleanup = () => {
      document.removeEventListener("keydown", onKey, true);
      document.removeEventListener("focusin", onFocusMove, true);
      document.removeEventListener("focusout", onFocusMove, true);
    };
  }
  function stopMonitor() {
    if (monitorCleanup) monitorCleanup();
    monitorCleanup = null;
    monitoredRoot = null;
  }

  // ---- Jugador de fallback (loop en la página) -------------------------------
  async function runPlan(plan, cfg, respond) {
    const delay = makeHumanizer(cfg);
    const root0 = editableRoot();
    let stopped = false;
    let abortReason = null;
    stopTyping = () => { stopped = true; };
    let execOk = true;
    let setterUsed = false;
    let prevCh = null;
    let lastPct = -1;

    const notify = (msg) => { try { chrome.runtime.sendMessage(msg); } catch (_) {} };

    for (let i = 0; i < plan.length; i++) {
      if (stopped) break;
      const step = plan[i];

      // El campo sigue siendo el mismo y sigue enfocado.
      const el = editableRoot();
      if (!el || el !== root0) { abortReason = "el foco del campo cambió"; break; }

      let ms;
      if (step.pre === "typo-notice") ms = 120 + Math.random() * 280;
      else if (step.pre === "typo-fix") ms = 80 + Math.random() * 160;
      else ms = delay(prevCh);
      await sleep(ms);
      if (stopped) break;

      const el2 = editableRoot();
      if (!el2 || el2 !== root0) { abortReason = "el foco del campo cambió"; break; }
      const target = el2;

      try {
        if (step.t === "char") {
          const kInit = { key: step.key ?? step.text, code: step.code ?? "", keyCode: step.vk ?? 0, shift: !!step.shift };
          fireKey(target, "keydown", kInit);
          fireKey(target, "keypress", kInit);
          fireInputEvent(target, "beforeinput", step.text, "insertText");
          // execCommand con UN solo code point (regla A). Si devuelve true,
          // el navegador dispara el evento "input" correspondiente.
          let ok = false;
          try { ok = document.execCommand("insertText", false, step.text); } catch (_) {}
          if (ok) {
            // nada: ya hubo input nativo (no confiable, pero nativo)
          } else {
            // FALLBACK 2: setter nativo + evento input manual, mismo code point.
            setterUsed = true;
            insertViaSetter(target, step.text);
            fireInputEvent(target, "input", step.text, "insertText");
          }
          fireKey(target, "keyup", kInit);
          prevCh = step.text;
        } else if (step.t === "enter") {
          fireKey(target, "keydown", { key: "Enter", code: "Enter", keyCode: 13 });
          fireInputEvent(target, "beforeinput", undefined, "insertLineBreak");
          let ok = false;
          if (target.isContentEditable) {
            try { ok = document.execCommand("insertLineBreak"); } catch (_) {}
            if (!ok) { try { ok = document.execCommand("insertParagraph"); } catch (_) {} }
          }
          if (!ok) { try { ok = document.execCommand("insertText", false, "\n"); } catch (_) {} }
          if (!ok) {
            setterUsed = true;
            insertViaSetter(target, "\n");
            fireInputEvent(target, "input", "\n", "insertLineBreak");
          }
          fireKey(target, "keyup", { key: "Enter", code: "Enter", keyCode: 13 });
          prevCh = "\n";
        } else if (step.t === "bs") {
          fireKey(target, "keydown", { key: "Backspace", code: "Backspace", keyCode: 8 });
          fireInputEvent(target, "beforeinput", undefined, "deleteContentBackward");
          let ok = false;
          try { ok = document.execCommand("delete"); } catch (_) {}
          if (!ok) {
            setterUsed = true;
            deleteAtCaret(target);
            fireInputEvent(target, "input", undefined, "deleteContentBackward");
          }
          fireKey(target, "keyup", { key: "Backspace", code: "Backspace", keyCode: 8 });
        }
      } catch (e) {
        abortReason = "error insertando: " + (e && e.message);
        break;
      }

      const pct = Math.round(((i + 1) / plan.length) * 100);
      if (pct !== lastPct) { lastPct = pct; notify({ tc: "progress", pct }); }
    }

    stopTyping = null;
    if (abortReason) notify({ tc: "editable-changed" }); // el SW también aborta por su lado
    respond({
      ok: true,
      status: abortReason ? "aborted" : stopped ? "cancelled" : "done",
      execOk: !setterUsed,
      setterUsed,
      reason: abortReason || undefined,
    });
  }

  // ---- Despachador de mensajes del service worker ----------------------------
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || !msg.tc) return;
    switch (msg.tc) {
      case "init": {
        const el = editableRoot();
        sendResponse({
          ok: !!el,
          reason: el ? undefined : "el foco no está en un input/textarea/contenteditable",
          kind: el ? (el.isContentEditable ? "contenteditable" : el.tagName.toLowerCase()) : undefined,
        });
        return false;
      }
      case "start-monitor":
        startMonitor();
        sendResponse({ ok: true });
        return false;
      case "stop-monitor":
        stopMonitor();
        sendResponse({ ok: true });
        return false;
      case "read":
        sendResponse({ ok: true, text: fieldText(editableRoot()) });
        return false;
      case "exec-type":
        runPlan(msg.plan, msg.settings || {}, sendResponse);
        return true; // respuesta asincrónica al finalizar el tipeo
      case "stop-type":
        if (stopTyping) stopTyping();
        sendResponse({ ok: true });
        return false;
    }
  });
}

// Estado al momento de la inyección: chrome.scripting.executeScript captura el
// valor de la ÚLTIMA sentencia del archivo, y el SW lo usa para saber si ESTE
// frame es el que tiene el campo editable enfocado. Va FUERA del guard para
// ejecutarse en cada inyección (las funciones persisten del primer load, mismo
// mundo aislado).
(() => {
  const el = typeof editableRoot === "function" ? editableRoot() : null;
  return {
    ok: !!el,
    reason: el ? undefined : "el foco no está en un input/textarea/contenteditable",
    kind: el ? (el.isContentEditable ? "contenteditable" : el.tagName.toLowerCase()) : undefined,
  };
})();
