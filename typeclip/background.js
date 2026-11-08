// TypeClip — background.js (service worker MV3)
//
// Flujo de una invocación (atajo Alt+Shift+V o click en el ícono):
//   1. Si ya hay un tipeo corriendo → cancelarlo (el atajo es un toggle).
//   2. Verificar pestaña activa + ventana con foco (regla B).
//   3. Inyectar content.js y verificar que document.activeElement sea editable.
//   4. Leer el portapapeles AHORA, vía offscreen document (regla: nunca antes).
//   5. Construir el "plan" de tipeo (code points, con typos expandidos).
//   6. Método principal: chrome.debugger + CDP (Input.dispatchKeyEvent).
//      Si el attach falla → fallback: el content script dispara eventos + execCommand.
//   7. Verificación final contra el texto del portapapeles; badge OK / DIF / ERR.
//
// Reglas no negociables que este archivo respeta:
//   - Nunca más de UN code point por evento de input (ningún método).
//   - Nunca eventos "paste" ni DataTransfer sobre la página del sitio.
//   - inputTypes permitidos en el sitio: insertText, insertLineBreak,
//     insertParagraph (Enter) y deleteContentBackward (Backspace de typos).
//   - El texto vive solo en memoria: sin logs del contenido, sin storage, sin red.

/* global chrome, TextEncoder */

// ---------------------------------------------------------------------------
// Configuración
// ---------------------------------------------------------------------------

const DEFAULTS = {
  wpm: 100,       // velocidad base (40–250)
  jitter: 50,     // variación humana % (sigma lognormal /100)
  pauses: true,   // pausas extra tras espacio / puntuación / salto de línea
  thinkPct: 2,    // % de pausas de "pensar"
  typos: false,   // simular errores (default OFF)
  typoPct: 1.5,   // % de error por caracter
  tabMode: "spaces",
  tabSpaces: 4,
};

let settings = { ...DEFAULTS };

// ---------------------------------------------------------------------------
// Mapa de teclas US (key / code / windowsVirtualKeyCode)
// Es el layout de referencia; los caracteres fuera de este mapa van por la
// vía "text directo" (ver abajo) y los astrales por Input.insertText unitario.
// ---------------------------------------------------------------------------

const KEYMAP = {};
for (let i = 0; i < 26; i++) {
  const L = String.fromCharCode(65 + i); // 'A'
  const l = String.fromCharCode(97 + i); // 'a'
  KEYMAP[l] = { key: l, code: "Key" + L, vk: 65 + i, shift: false };
  KEYMAP[L] = { key: L, code: "Key" + L, vk: 65 + i, shift: true };
}
for (let d = 0; d < 10; d++) {
  KEYMAP[String(d)] = { key: String(d), code: "Digit" + d, vk: 48 + d, shift: false };
}
KEYMAP[" "] = { key: " ", code: "Space", vk: 32, shift: false };
// [caracter, code, vk, shift?]
const SYMBOLS = [
  ["!", "Digit1", 49, true], ["@", "Digit2", 50, true], ["#", "Digit3", 51, true],
  ["$", "Digit4", 52, true], ["%", "Digit5", 53, true], ["^", "Digit6", 54, true],
  ["&", "Digit7", 55, true], ["*", "Digit8", 56, true], ["(", "Digit9", 57, true],
  [")", "Digit0", 58, true],
  ["-", "Minus", 189, false], ["_", "Minus", 189, true],
  ["=", "Equal", 187, false], ["+", "Equal", 187, true],
  ["[", "BracketLeft", 219, false], ["{", "BracketLeft", 219, true],
  ["]", "BracketRight", 221, false], ["}", "BracketRight", 221, true],
  ["\\", "Backslash", 220, false], ["|", "Backslash", 220, true],
  [";", "Semicolon", 186, false], [":", "Semicolon", 186, true],
  ["'", "Quote", 222, false], ['"', "Quote", 222, true],
  ["`", "Backquote", 192, false], ["~", "Backquote", 192, true],
  [",", "Comma", 188, false], ["<", "Comma", 188, true],
  [".", "Period", 190, false], [">", "Period", 190, true],
  ["/", "Slash", 191, false], ["?", "Slash", 191, true],
];
for (const [ch, code, vk, shift] of SYMBOLS) KEYMAP[ch] = { key: ch, code, vk, shift };

// Vecinos QWERTY para los errores de tipeo (mismo layout físico, teclas contiguas).
const QWERTY_NEIGHBORS = {
  q: "wa", w: "qes", e: "wrd", r: "etf", t: "ryg", y: "tuh", u: "yij", i: "uok", o: "ipl", p: "ol",
  a: "qwsz", s: "aedx", d: "erfc", f: "rtgv", g: "tyhb", h: "yujn", j: "uikm", k: "iol", l: "opk",
  z: "asx", x: "zsdc", c: "xdfv", v: "cfgb", b: "vghn", n: "bhjm", m: "njk",
};

// ¿El code point está fuera del BMP? (emoji, etc. — pares surrogate)
function isAstral(ch) {
  const cp = ch.codePointAt(0);
  return cp > 0xffff;
}

// Para caracteres fuera del layout US (ñ, á, ü…): aproximar la tecla base
// quitando diacríticos (NFD). Ej.: 'ñ' → tecla N (vk 78). Sirve para que los
// editores que miran e.keyCode vean algo coherente; la inserción real va por `text`.
function baseKeyInfo(ch) {
  const decomposed = ch.normalize("NFD");
  const base = decomposed[0];
  const m = KEYMAP[base];
  if (m && !m.shift) return { key: ch, code: m.code, vk: m.vk, shift: false, special: true };
  return { key: ch, code: undefined, vk: 0, shift: false, special: true };
}

// ---------------------------------------------------------------------------
// Plan de tipeo: lista de pasos que ambos "jugadores" (CDP y content script)
// ejecutan con la misma humanización. Un paso por code point como máximo.
// ---------------------------------------------------------------------------

function charStep(ch) {
  const m = KEYMAP[ch];
  if (m) return { t: "char", text: ch, key: m.key, code: m.code, vk: m.vk, shift: m.shift };
  if (isAstral(ch)) return { t: "char", text: ch, astral: true }; // → Input.insertText de 1 code point
  return { t: "char", text: ch, ...baseKeyInfo(ch) }; // vía "text directo", verificada en vivo
}

function buildPlan(rawText, cfg) {
  const text = rawText.replace(/\r\n?/g, "\n");
  const cps = Array.from(text); // iterar por code points, nunca por code units
  const steps = [];
  for (let i = 0; i < cps.length; i++) {
    const ch = cps[i];
    if (ch === "\n") { steps.push({ t: "enter" }); continue; }
    if (ch === "\t") {
      // Un Tab real movería el foco: se reemplaza según configuración.
      if (cfg.tabMode === "skip") continue;
      for (let k = 0; k < cfg.tabSpaces; k++) steps.push(KEYMAP[" "] ? charStep(" ") : { t: "char", text: " " });
      continue;
    }
    // Errores de tipeo: solo letras, nunca en el último caracter del texto.
    if (cfg.typos && i < cps.length - 1 && /[a-zA-Z]/.test(ch)) {
      if (Math.random() * 100 < cfg.typoPct) {
        const neighbors = QWERTY_NEIGHBORS[ch.toLowerCase()] || "";
        if (neighbors) {
          const wrong = neighbors[Math.floor(Math.random() * neighbors.length)];
          const wrongCh = ch === ch.toLowerCase() ? wrong : wrong.toUpperCase();
          steps.push(charStep(wrongCh));              // teclea la tecla vecina...
          steps.push({ t: "bs", pre: "typo-notice" }); // ...lo nota (pausa)...
          const fix = charStep(ch); fix.pre = "typo-fix";
          steps.push(fix);                             // ...y corrige con Backspace.
          continue;
        }
      }
    }
    steps.push(charStep(ch));
  }
  return steps;
}

// ---------------------------------------------------------------------------
// Humanización de delays (log-normal alrededor de la base; nunca constante).
// La misma lógica está duplicada en content.js para el fallback — mantener
// sincronizadas las dos copias.
// ---------------------------------------------------------------------------

function makeHumanizer(cfg) {
  const base = 60000 / (Math.max(10, cfg.wpm) * 5); // ms por caracter (5 caracteres/palabra)
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
  // Delay ANTES del caracter `next`, considerando qué se tipeó antes (`prevCh`).
  return function delay(prevCh) {
    let d = Math.exp(Math.log(base) - (s * s) / 2 + s * gauss()); // mediana = base
    d = Math.min(Math.max(d, base * 0.25), base * 4);
    if (cfg.pauses && prevCh) {
      if (prevCh === "\n") d *= 4 + Math.random() * 4;               // salto de línea
      else if (prevCh === " ") d *= 1.8 + Math.random() * 1.2;       // espacio
      else if (".;:!?".includes(prevCh)) d *= 2.5 + Math.random() * 2.5; // puntuación fuerte
      else if (prevCh === ",") d *= 2 + Math.random() * 1.5;
    }
    if (Math.random() * 100 < cfg.thinkPct) d += 500 + Math.random() * 1000; // pausa de pensar
    return d;
  };
}

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

// Ring-buffer de diagnóstico (solo eventos de control, NUNCA texto tipeado).
// El arnés E2E lo lee con sw.evaluate(() => globalThis.__typeclipDbg()).
globalThis.__dbgLog = [];
function dbglog(ev, data) {
  const t = globalThis.__dbgLog;
  t.push(`[${new Date().toISOString().slice(11, 23)}] ${ev}` + (data !== undefined ? ` ${data}` : ""));
  if (t.length > 300) t.splice(0, t.length - 300);
}
globalThis.__typeclipDbg = () => globalThis.__dbgLog.slice();

function badge(text, color, tooltip) {
  dbglog("badge", JSON.stringify(text) + (tooltip ? " · " + tooltip.slice(0, 60) : ""));
  chrome.action.setBadgeText({ text: text || "" });
  if (color) chrome.action.setBadgeBackgroundColor({ color });
  if (tooltip !== undefined) chrome.action.setTitle({ title: tooltip });
}

const COLOR_RUN = "#2563eb", COLOR_OK = "#16a34a", COLOR_ERR = "#dc2626", COLOR_WARN = "#d97706";

// ---------------------------------------------------------------------------
// Estado de sesión
// ---------------------------------------------------------------------------

let session = null; // {tabId, frameId, method, cancel:false, attached:false, end:resolve...}

// ---------------------------------------------------------------------------
// Limpieza de arranque: si Chrome terminó el service worker a mitad de una
// sesión, el attach del debugger queda HUÉRFANO (el cartel amarillo no se va
// nunca), el badge queda clavado en un porcentaje y el content script sigue
// monitoreando/tragando Esc. Al renacer el SW: desprender lo nuestro y limpiar.
// chrome.debugger.detach solo afecta el attach DE ESTA extensión, así que
// probarlo contra tabs donde el "attached" es de otro (DevTools del usuario,
// otro DevTools client) falla silenciosamente y no toca nada ajeno.
// ---------------------------------------------------------------------------
chrome.debugger.getTargets().then((targets) => {
  const orphans = targets.filter((t) => t.attached && typeof t.tabId === "number");
  for (const t of orphans) {
    chrome.debugger.detach({ tabId: t.tabId }).then(() => {
      dbglog("stale", `attach huérfano desprendido (tab ${t.tabId}) al renacer el SW`);
      badge("", null, chrome.runtime.getManifest().action.default_title);
      sendToContent(t.tabId, null, { tc: "stop-monitor" });
    }).catch(() => { /* el attach no era nuestro */ });
  }
}).catch(() => { /* sin permiso para listar: no hacer nada */ });

// ---------------------------------------------------------------------------
// Clipboard vía offscreen document (única forma de leerlo desde el SW de MV3)
// ---------------------------------------------------------------------------

let offscreenCreating = null;
async function withOffscreen(fn) {
  try {
    if (!(await chrome.offscreen.hasDocument?.() ?? false)) {
      offscreenCreating ??= chrome.offscreen.createDocument({
        url: "offscreen.html",
        reasons: ["CLIPBOARD"],
        justification: "Leer el texto del portapapeles para tipearlo en el campo enfocado",
      }).finally(() => { offscreenCreating = null; });
      await offscreenCreating;
    }
  } catch (e) {
    // "Only a single offscreen document" → ya existe, seguir.
    if (!String(e).includes("single offscreen")) throw e;
  }
  try {
    return await fn();
  } finally {
    try { await chrome.offscreen.closeDocument(); } catch (_) { /* ya cerrado */ }
  }
}

function readClipboardViaOffscreen() {
  return withOffscreen(() => new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ ok: false, error: "timeout leyendo el portapapeles" }), 4000);
    chrome.runtime.sendMessage({ tc: "read-clipboard" }, (resp) => {
      clearTimeout(timer);
      if (chrome.runtime.lastError) return resolve({ ok: false, error: chrome.runtime.lastError.message });
      resolve(resp || { ok: false, error: "sin respuesta del offscreen document" });
    });
  }));
}

// ---------------------------------------------------------------------------
// Inyección del content script y mensajes hacia él
// ---------------------------------------------------------------------------

async function injectContentScript(tabId) {
  // allFrames: el campo editable puede estar en un iframe mismo-origen.
  // Guard: content.js se auto-ignora si ya estaba inyectado.
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      files: ["content.js"],
    });
    return results.map((r) => ({ frameId: r.frameId, ...r.result }));
  } catch (e) {
    // La inyección puede fallar porque la página no lo permite (chrome://,
    // Web Store…) o porque el content script YA está presente en la página
    // (p.ej. la página de prueba propia de la extensión, que lo carga sola).
    // Sondear por mensaje antes de rendirse.
    const probe = await sendToContent(tabId, null, { tc: "init" });
    if (probe && probe.ok) return [{ frameId: null, ...probe }];
    throw e;
  }
}

function sendToContent(tabId, frameId, msg) {
  return new Promise((resolve) => {
    const opts = frameId != null ? { frameId } : {};
    chrome.tabs.sendMessage(tabId, msg, opts, (resp) => {
      if (chrome.runtime.lastError) return resolve({ ok: false, error: chrome.runtime.lastError.message });
      resolve(resp ?? { ok: false, error: "sin respuesta" });
    });
  });
}

// Lectura del campo con timeout: un renderer trabado no contesta mensajes
// tampoco — sin esto, la sonda de caracteres especiales quedaría colgada
// esperando una respuesta que no llega nunca. Al vencer, se trata como
// "no insertado" y el flujo sigue (el próximo cdp() vence su propio timeout
// y aborta la sesión con detach).
function readWithTimeout(tabId, frameId, ms) {
  return Promise.race([
    sendToContent(tabId, frameId, { tc: "read" }),
    new Promise((resolve) => setTimeout(() => resolve({ ok: false, error: "read timeout" }), ms)),
  ]);
}

// ---------------------------------------------------------------------------
// Invocación
// ---------------------------------------------------------------------------

chrome.commands.onCommand.addListener((command) => {
  if (command === "type-clipboard") invoke();
});

chrome.action.onClicked.addListener((tab) => invoke());

let invoking = false;
async function invoke() {
  dbglog("invoke", session ? "(toggle→cancel)" : "(nueva sesión)");
  if (session) { await cancel("cancelado por el usuario"); return; } // re-invocar = cancelar
  if (invoking) return;
  invoking = true;
  try { await runSession(); } catch (e) { console.warn("TypeClip:", e); dbglog("runSession throw", e.message); }
  finally { invoking = false; }
}

async function runSession() {
  await loadSettings();

  // --- Regla B: solo la pestaña activa, visible y con foco de ventana. ---
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!tab || !tab.id) return badge("ERR", COLOR_ERR, "TypeClip: no hay pestaña activa");
  if (!tab.url) {
    session = null;
    return badge("ERR", COLOR_ERR, "TypeClip: la pestaña no expone URL; no se puede operar");
  }
  const win = await chrome.windows.get(tab.windowId);
  if (!tab.active) return badge("ERR", COLOR_ERR, "TypeClip: la pestaña no está activa");
  if (!win.focused) return badge("ERR", COLOR_ERR, "TypeClip: la ventana no tiene el foco — hacé click en la página y volvé a invocar");

  session = { tabId: tab.id, frameId: null, method: null, cancel: false, attached: false };

  // --- 1) Verificar campo editable (content.js responde por frame). ---
  let frames;
  try {
    frames = await injectContentScript(tab.id);
  } catch (e) {
    session = null;
    return badge("ERR", COLOR_ERR, "TypeClip: esta página no permite inyectar scripts (chrome://, Web Store…) — nada que tipear");
  }
  const editableFrame = frames.find((f) => f && f.ok);
  if (!editableFrame) {
    session = null;
    const why = frames[0] && frames[0].reason;
    return badge("ERR", COLOR_ERR, "TypeClip: el elemento con foco no es editable (" + (why || "input/textarea/contenteditable") + "). Hacé click en el campo y reintentá.");
  }
  session.frameId = editableFrame.frameId;

  // --- 2) Leer el portapapeles AHORA (en el momento de la invocación). ---
  const clip = await readClipboardViaOffscreen();
  if (!clip.ok) {
    session = null;
    return badge("ERR", COLOR_ERR, "TypeClip: no se pudo leer el portapapeles (" + clip.error + ")");
  }
  if (!clip.text || !clip.text.trim()) {
    session = null;
    return badge("ERR", COLOR_ERR, "TypeClip: el portapapeles está vacío");
  }
  const clipboardText = clip.text; // vive solo en memoria; nunca se loguea ni se guarda

  // --- 2b) Inputs de una sola línea: NUNCA despachar Enter. Un Enter real
  // (keyDown con text "\r") en un <input> dispara el default action de Chrome
  // (submit del <form> que lo contenga, más el evento change). Los saltos se
  // colapsan a UN espacio antes de armar el plan; ese mismo texto (ya sin
  // saltos) es también el esperado en la verificación final. ---
  let textToType = clipboardText;
  if (editableFrame.kind === "input") {
    textToType = clipboardText.replace(/\r\n?/g, "\n").replace(/\n+/g, " ");
    dbglog("singleline", "input de una línea: saltos colapsados a espacios (anti-submit)");
  }

  // --- 2c) Línea base del campo ANTES de tipear. Sin esto, un campo que ya
  // tenía texto daría DIF siempre en la verificación final (nunca puede
  // "coincidir" con el portapapeles entero). Queda solo en memoria, como
  // todo el texto que pasa por acá: nunca se loguea ni se guarda. ---
  const baseRead = await sendToContent(tab.id, editableFrame.frameId, { tc: "read" });
  const baseline = baseRead.ok ? (baseRead.text ?? "") : "";
  if (!session) return; // cancel() durante el arranque: cancel ya limpió todo

  // --- 3) Armar el plan y arrancar los monitores del content script. ---
  const plan = buildPlan(textToType, settings);
  if (!plan.length) { session = null; return badge("ERR", COLOR_ERR, "TypeClip: nada tipeable en el portapapeles"); }
  const frameId = editableFrame.frameId; // capturado: cancel() puede anular session
  await sendToContent(tab.id, frameId, { tc: "start-monitor" });
  if (!session) { // cancel() llegó durante el arranque: no dejar el monitor vivo
    await sendToContent(tab.id, frameId, { tc: "stop-monitor" });
    return;
  }
  startGlobalMonitors();

  // --- 4) Método principal: chrome.debugger + CDP; si falla, fallback JS.
  // Si cancel() llega durante el attach, el debugger hay que soltarlo ACÁ:
  // nadie más lo haría y quedaría el infobar colgado en la pestaña. ---
  let attached = false;
  try {
    await chrome.debugger.attach({ tabId: tab.id }, "1.3");
    attached = true;
  } catch (e) { /* attach falla → fallback JS */ }
  if (!session) { // cancel() durante el arranque
    stopGlobalMonitors();
    if (attached) { try { await chrome.debugger.detach({ tabId: tab.id }); } catch (_) { /* ya desprendido */ } }
    await sendToContent(tab.id, frameId, { tc: "stop-monitor" });
    return;
  }
  session.attached = attached;

  const human = makeHumanizer(settings);
  startKeepalive();
  let outcome;
  if (attached) {
    session.method = "CDP";
    badge("0%", COLOR_RUN, "TypeClip: tipeando · método CDP (chrome.debugger) · Esc o Alt+Shift+V para cancelar");
    outcome = await playCdp(plan, human);
  } else {
    session.method = "JS";
    badge("0%", COLOR_RUN, "TypeClip: tipeando · método eventos JS (isTrusted=false; ver README) · Esc para cancelar");
    outcome = await playViaContentScript(plan);
  }

  stopGlobalMonitors();
  stopKeepalive();
  dbglog("outcome", outcome.status + " " + (outcome.method || "") +
    (outcome.reason ? " · " + outcome.reason : "") +
    " session=" + (session ? "viva" : "null"));
  // Detach del debugger apenas termina el tipeo (el infobar debe irse ya).
  // Marcar attached=false ANTES: el detach propio no debe disparar el onDetach
  // que trataría la sesión como abortada.
  if (session?.attached) {
    session.attached = false;
    try { await chrome.debugger.detach({ tabId: tab.id }); } catch (_) { /* ya desprendido */ }
  }
  if (!session) return; // abort()/cancel() ya limpiaron todo
  const s = session; // desde acá, cancel() puede anular session en cualquier await

  // --- 5) Verificación final contra el texto del portapapeles. ---
  const methodLabel = outcome.method || s.method;
  if (outcome.status === "cancelled") {
    session = null;
    return; // cancel() ya hizo detach + badge limpio
  }
  if (outcome.status === "aborted") {
    badge("ERR", COLOR_ERR, "TypeClip: abortado — " + outcome.reason);
    session = null;
    setTimeout(() => badge("", null, "TypeClip — tipear el portapapeles (Alt+Shift+V)"), 6000);
    return;
  }

  const finalRead = await sendToContent(s.tabId, s.frameId, { tc: "read" });
  await sendToContent(s.tabId, s.frameId, { tc: "stop-monitor" });
  session = null;

  // Verificación contra la línea base (texto que el campo YA tenía antes del
  // tipeo). El OK exige evidencia de que el tipeo quedó: que "expected" aparezca
  // MÁS veces que en la línea base. Con "includes" a secas, un campo precargado
  // con exactamente el texto del portapapeles daba un OK falso aunque el tipeo
  // no hubiera entrado nada.
  const expected = normalizeForCompare(textToType);
  const got = finalRead.ok ? normalizeForCompare(finalRead.text ?? "") : "";
  const baseNorm = normalizeForCompare(baseline);
  const nGot = countOccurrences(got, expected);
  const nBase = countOccurrences(baseNorm, expected);
  const grew = finalRead.ok && !!baseNorm && nGot > nBase && got.length >= baseNorm.length;
  if (finalRead.ok && !baseNorm && expected === got) {
    // Línea base vacía: el campo debe quedar exactamente con el portapapeles.
    badge("OK", COLOR_OK, "TypeClip: listo · método " + methodLabel + " · el campo coincide con el portapapeles");
  } else if (grew) {
    // El campo ya tenía texto: el tipeo quedó insertado adentro (el caret pudo
    // estar en cualquier posición). Exige que las ocurrencias hayan crecido.
    badge("OK", COLOR_OK, "TypeClip: listo · método " + methodLabel + " · el tipeo quedó insertado (el campo ya tenía texto)");
  } else if (finalRead.ok) {
    badge("DIF", COLOR_WARN,
      "TypeClip: terminó (método " + methodLabel + ") pero el campo NO coincide con el portapapeles" +
      detailDiff(expected, got) + ". ¿Typeahead de @menciones, autocorrección o maxLength?");
  } else {
    badge("OK?", COLOR_WARN, "TypeClip: terminó (método " + methodLabel + "); no se pudo leer el campo para verificar (" + finalRead.error + ")");
  }
}

function detailDiff(expected, got) {
  let i = 0;
  while (i < expected.length && i < got.length && expected[i] === got[i]) i++;
  return ` (coinciden ${i} caracteres; esperado ${expected.length}, el campo tiene ${got.length})`;
}

function normalizeForCompare(t) {
  return t
    .normalize("NFC")
    .replace(/\r\n?/g, "\n")   // saltos de línea uniformes
    .replace(/[ \t]+$/gm, "")  // espacios de relleno al final de línea
    .replace(/\n{3,}/g, "\n\n") // párrafos vacíos múltiples
    .trim();
}

// Ocurrencias NO solapadas de needle en haystack (para la verificación contra
// línea base: el tipeo cuenta como hecho solo si "expected" apareció más veces
// de las que ya había antes de tipear).
function countOccurrences(haystack, needle) {
  if (!needle) return 0;
  let n = 0;
  let i = haystack.indexOf(needle);
  while (i !== -1) {
    n++;
    i = haystack.indexOf(needle, i + needle.length);
  }
  return n;
}

// ---------------------------------------------------------------------------
// Jugador principal: chrome.debugger (CDP). Cada sendCommand resetea el timer
// de inactividad del service worker (más el keepalive de abajo).
// ---------------------------------------------------------------------------

function cdp(tabId, method, params) {
  // Timeout de seguridad: si el renderer de la pestaña se trabó (medido: un
  // editor que muta el DOM dentro de su handler de input a mitad de un commit
  // IME puede dejar un Input.dispatchKeyEvent sin respuesta PARA SIEMPRE —
  // sesión colgada con el cartel amarillo puesto), abortamos y desprendemos.
  // El RTT normal de un comando es ~80 ms; 15 s es margen de sobra.
  // IMPORTANTE: el timer se CANCELA cuando el comando responde. Con
  // Promise.race pelado, cada comando exitoso dejaba un setTimeout vivo que
  // 15 s después rechazaba una promise ya resuelta y ensuciaba el log (en una
  // sesión de 2000 caracteres, ~8000 timers basura disparando a la vez).
  return new Promise((resolve, reject) => {
    let done = false;
    const timer = setTimeout(() => {
      if (done) return;
      done = true;
      reject(new Error("timeout " + method));
    }, 15000);
    chrome.debugger.sendCommand({ tabId }, method, params || {}, (result) => {
      if (done) return; // ya expiró el timeout; la respuesta tardía se ignora
      done = true;
      clearTimeout(timer);
      const err = chrome.runtime.lastError;
      if (err) reject(new Error(err.message)); else resolve(result);
    });
  });
}

function keyEvent(type, o) {
  // Evento de teclado CDP con los campos que Chrome usa para sintetizar
  // keydown/keypress/beforeinput/input con isTrusted=true.
  // NOTA: NO se envía `timestamp`: CDP lo espera en SEGUNDOS desde epoch y un
  // Date.now() en milisegundos dejaba el event.timeStamp del sitio ~1.7e15 ms
  // a futuro (medido) — justo en la parte que quiere verse como teclado real.
  // Sin el campo, Chrome estampa la hora actual (igual que Puppeteer).
  const ev = {
    type,
    modifiers: o.modifiers || 0,
    key: o.key,
    code: o.code || "",
    windowsVirtualKeyCode: o.vk || 0,
    nativeVirtualKeyCode: o.vk || 0,
    autoRepeat: false,
    location: 0,
    isKeypad: false,
  };
  if (o.text !== undefined) { ev.text = o.text; ev.unmodifiedText = o.text; }
  return ev;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function playCdp(plan, delayFn) {
  const tabId = session.tabId;
  const frameId = session.frameId; // capturado: cancel() puede anular session
  dbglog("playCdp inicia", "plan=" + plan.length + " pasos");
  const specialVerified = new Set();   // code points no-US ya verificados vía keyDown+text
  const specialNeedInsert = new Set(); // code points no-US que NO insertan y van por insertText
  const insertSingle = async (cp) => {
    // Inserta UN solo code point (regla A). Nada de strings largos "para acelerar".
    await cdp(tabId, "Input.insertText", { text: cp });
  };
  // Orden real de un caracter con Shift: Shift↓, tecla↓, tecla↑, Shift↑.
  const playCharKey = async (step) => {
    const mods = step.shift ? 8 : 0;
    const inner = async () => {
      await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyDown", {
        key: step.key, code: step.code, vk: step.vk, text: step.text, modifiers: mods,
      }));
      await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyUp", {
        key: step.key, code: step.code, vk: step.vk, modifiers: mods,
      }));
    };
    if (!step.shift) return inner();
    await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyDown", { key: "Shift", code: "ShiftLeft", vk: 16 }));
    await inner();
    await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyUp", { key: "Shift", code: "ShiftLeft", vk: 16 }));
  };

  let prevCh = null;
  let lastPct = -1;
  for (let i = 0; i < plan.length; i++) {
    if (!session || session.cancel || session.tabId !== tabId) return { status: "cancelled" };
    const step = plan[i];

    // Delay humanizado antes del paso.
    let ms;
    if (step.pre === "typo-notice") ms = 120 + Math.random() * 280;
    else if (step.pre === "typo-fix") ms = 80 + Math.random() * 160;
    else ms = delayFn(prevCh);
    await sleep(ms);
    if (!session || session.cancel || session.tabId !== tabId) return { status: "cancelled" };

    try {
      if (step.t === "char") {
        if (step.astral || specialNeedInsert.has(step.text)) {
          await insertSingle(step.text); // emoji / verificado-que-falla: UN code point
        } else {
          // keyDown con `text` genera keydown → keypress → beforeinput(insertText) → input.
          // Sonda de caracteres fuera del layout US (ñ, á, ¿…): la PRIMERA vez
          // que aparece cada uno, verificar que el keyDown lo insertó DE VERDAD.
          // Se compara el LARGO del campo antes/después — mirar la cola asumía
          // caret al final y duplicaba el caracter si estaba en el medio — y se
          // espera hasta ~150 ms porque hay editores que insertan async
          // (Lexical, ProseMirror…). Si no entró → Input.insertText de ese
          // único code point (regla del spec).
          const needProbe = step.special && !specialVerified.has(step.text);
          let len0 = -1;
          if (needProbe) {
            const r0 = await readWithTimeout(tabId, frameId, 2000);
            if (r0.ok) len0 = Array.from(r0.text || "").length;
          }
          await playCharKey(step);
          if (needProbe) {
            let inserted = false;
            for (let waited = 0; waited <= 150 && !inserted; waited += 25) {
              const r = await readWithTimeout(tabId, frameId, 2000);
              if (r.ok && Array.from(r.text || "").length > len0) inserted = true;
              else await sleep(25);
            }
            if (inserted) {
              specialVerified.add(step.text);
              dbglog("probe@" + i, "ok (cp " + step.text.codePointAt(0) + ")");
            } else {
              specialNeedInsert.add(step.text);
              dbglog("probe@" + i, "cayó a insertText (cp " + step.text.codePointAt(0) + ")");
              await insertSingle(step.text); // el keyDown no insertó → insertText de 1 cp
            }
          }
        }
        prevCh = step.text;
      } else if (step.t === "enter") {
        // Enter real: VK 13, text "\r" → beforeinput insertParagraph/insertLineBreak.
        await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyDown", { key: "Enter", code: "Enter", vk: 13, text: "\r" }));
        await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyUp", { key: "Enter", code: "Enter", vk: 13 }));
        prevCh = "\n";
      } else if (step.t === "bs") {
        await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyDown", { key: "Backspace", code: "Backspace", vk: 8 }));
        await cdp(tabId, "Input.dispatchKeyEvent", keyEvent("keyUp", { key: "Backspace", code: "Backspace", vk: 8 }));
        // prevCh queda: después del backspace viene el caracter corregido.
      }
    } catch (e) {
      return { status: "aborted", reason: "CDP: " + e.message };
    }

    const pct = Math.round(((i + 1) / plan.length) * 100);
    if (pct !== lastPct) {
      lastPct = pct;
      chrome.action.setBadgeText({ text: pct + "%" });
    }
    if ((i + 1) % 200 === 0) dbglog("plan@" + (i + 1), pct + "%");  }
  return { status: "done", method: "CDP" };
}

// ---------------------------------------------------------------------------
// Fallback: el loop corre DENTRO de la página (content.js), evento por evento.
// El SW solo espera el resultado (los mensajes de progreso lo mantienen vivo).
// ---------------------------------------------------------------------------

async function playViaContentScript(plan) {
  const r = await sendToContent(session.tabId, session.frameId, {
    tc: "exec-type",
    plan,
    settings,
  });
  if (!r.ok) return { status: "aborted", reason: "fallback JS: " + (r.error || "falló") };
  if (r.status === "cancelled" || r.status === "aborted") return r;
  // Si algún caracter necesitó el setter nativo, se informa (JS/SET).
  return { status: "done", method: r.setterUsed ? "JS/SET" : "JS" };
}

// ---------------------------------------------------------------------------
// Cancelación y aborts limpios
// ---------------------------------------------------------------------------

async function cancel(reason) {
  if (!session) return;
  dbglog("cancel", reason);
  session.cancel = true;
  const s = session;
  session = null; // corta el loop CDP de una
  stopGlobalMonitors();
  stopKeepalive();
  if (s.attached) {
    try { await chrome.debugger.detach({ tabId: s.tabId }); } catch (_) { /* ya desprendido */ }
  }
  sendToContent(s.tabId, s.frameId, { tc: "stop-type" });
  sendToContent(s.tabId, s.frameId, { tc: "stop-monitor" });
  badge("", null, "TypeClip — tipear el portapapeles (Alt+Shift+V)"); // limpia el badge
  console.info("TypeClip: sesión cancelada (" + reason + ")");
}

async function abortSession(reason) {
  // Abort por condiciones externas (foco perdido, pestaña cambiada, debugger cerrado).
  if (!session) return;
  dbglog("abort", reason);
  const s = session;
  session = null; // corta el loop de una
  stopGlobalMonitors();
  stopKeepalive();
  if (s.attached) {
    try { await chrome.debugger.detach({ tabId: s.tabId }); } catch (_) { /* ya desprendido */ }
  }
  sendToContent(s.tabId, s.frameId, { tc: "stop-type" });
  sendToContent(s.tabId, s.frameId, { tc: "stop-monitor" });
  badge("ERR", COLOR_ERR, "TypeClip: " + reason);
}

// El usuario cerró el infobar "Chrome está siendo depurado" (o la pestaña se cerró).
chrome.debugger.onDetach.addListener(async (source) => {
  if (session && source.tabId === session.tabId) {
    await abortSession("el depurador se desprendió (¿cerraste el infobar o la pestaña?)");
  }
});

chrome.debugger.onEvent.addListener(() => { /* los eventos CDP también refrescan el SW */ });

// ---------------------------------------------------------------------------
// Monitores globales (regla B: foco de ventana, pestaña activa, pestaña viva)
// ---------------------------------------------------------------------------

let monitorsOn = false;
function onFocusChanged(windowId) {
  if (!session) return;
  // WINDOW_ID_NONE = ninguna ventana de Chrome tiene el foco (el usuario se
  // fue a otra app). Si el foco cayó en otra ventana, tampoco seguimos.
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    abortSession("la ventana perdió el foco");
    return;
  }
  chrome.tabs.get(session.tabId, (t) => {
    if (session && t && t.windowId !== windowId) abortSession("la ventana perdió el foco");
  });
}
function onTabActivated(activeInfo) {
  if (session && activeInfo.tabId !== session.tabId) abortSession("cambiaste de pestaña");
}
function onTabRemoved(tabId) {
  if (session && tabId === session.tabId) {
    session = null;
    stopGlobalMonitors();
    stopKeepalive();
    badge("", null, "TypeClip");
  }
}
function startGlobalMonitors() {
  if (monitorsOn) return;
  monitorsOn = true;
  chrome.windows.onFocusChanged.addListener(onFocusChanged);
  chrome.tabs.onActivated.addListener(onTabActivated);
  chrome.tabs.onRemoved.addListener(onTabRemoved);
}
function stopGlobalMonitors() {
  if (!monitorsOn) return;
  monitorsOn = false;
  chrome.windows.onFocusChanged.removeListener(onFocusChanged);
  chrome.tabs.onActivated.removeListener(onTabActivated);
  chrome.tabs.onRemoved.removeListener(onTabRemoved);
}

// ---------------------------------------------------------------------------
// Mensajes del content script
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (!msg || !msg.tc) return;
  switch (msg.tc) {
    case "esc": // Esc presionado en la página (solo isTrusted=true) → cancelar
      if (session && sender.tab?.id === session.tabId) cancel("Esc");
      break;
    case "editable-changed": // cambió document.activeElement a mitad del tipeo
      if (session && sender.tab?.id === session.tabId) abortSession("el foco del campo cambió a mitad del tipeo");
      break;
    case "progress": // progreso del fallback JS (también mantiene vivo el SW)
      if (session && sender.tab?.id === session.tabId) {
        chrome.action.setBadgeText({ text: msg.pct + "%" });
      }
      break;
  }
});

// ---------------------------------------------------------------------------
// Keepalive liviano: cada llamada a una API de chrome resetea el timer de
// inactividad del SW. Los sendCommand ya lo hacen por sí solos; esto cubre
// pausas largas y el fallback (donde el loop vive en la página).
// ---------------------------------------------------------------------------

let keepaliveTimer = null;
function startKeepalive() {
  stopKeepalive();
  keepaliveTimer = setInterval(() => chrome.runtime.getPlatformInfo(() => {}), 15000);
}
function stopKeepalive() {
  if (keepaliveTimer) { clearInterval(keepaliveTimer); keepaliveTimer = null; }
}

// Arranque del SW: cargar settings.
async function loadSettings() {
  const { settings: stored } = await chrome.storage.sync.get({ settings: {} });
  settings = { ...DEFAULTS, ...(stored || {}) };
}
loadSettings();

// Al suspenderse el SW, soltar el timer (el debugger se desprende solo si el SW muere).
chrome.runtime.onSuspend.addListener(() => {
  stopKeepalive();
});
