"use strict";
// ---------------------------------------------------------------------------
// Payloads de prueba
// ---------------------------------------------------------------------------
const PAYLOADS = {
  simple: "Hola mundo, esto es una prueba simple de TypeClip.",
  especiales: "mañana ñoño ¿bien? ¡café!",
  multiline: "Primera línea del portapapeles.\nSegunda línea tras un salto.\n\nY una tercera, tras un salto doble.",
  x280: "Prueba del composer con 280+ caracteres: ñandú, garçon, ¿cómo estás?, ¡holaaa! Café con leche ☕ y un emoji de cohete 🚀.\nSegunda línea que termina mencionando a @pablo\nTercer línea: enough, already; testing: enter keys & symbols $100 * 3 = ?",
  largo: null, // se genera abajo
};
{
  let s = "";
  let i = 0; // índice propio: usar s.length % frases.length repetía la línea 1
  const frases = [
    "El ñandú corrió por la pampa hasta que el sol se puso.",
    "¿Cuánto cuesta un café con leche en París? ¡Depende del barrio!",
    "Párrafo con números 12345 y símbolos raros: @user #tag $50% & (más).",
    "Línea con emoji 🚀 y otro ☕ para probar pares surrogate.",
    "A quick brown fox jumps over the lazy dog, again and again.",
  ];
  while (s.length < 2200) { s += frases[i % frases.length] + "\n"; i++; }
  PAYLOADS.largo = s;
}
// Fuente de verdad única para el arnés E2E (evita drift entre generadores).
window.__payloads = PAYLOADS;

document.getElementById("clipStatus").textContent = "";
async function copyToClipboard(t) {
  // 1) Async Clipboard API (http con permiso, o gestos con permiso otorgado).
  try { await navigator.clipboard.writeText(t); return true; } catch (e) { /* seguir */ }
  // 2) execCommand("copy") con selección: funciona con gesto de usuario real
  //    (el click) incluso en páginas de extensión sin clipboardWrite.
  const ta = document.getElementById("copybuf");
  ta.value = t;
  ta.focus();
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (_) {}
  ta.blur();
  ta.value = "";
  return ok;
}
for (const b of document.querySelectorAll("[data-payload]")) {
  b.addEventListener("click", async () => {
    const t = PAYLOADS[b.dataset.payload];
    const ok = await copyToClipboard(t);
    document.getElementById("clipStatus").textContent = ok
      ? "✓ copiado (" + Array.from(t).length + " code points)"
      : "✗ no se pudo copiar";
  });
}

// ---------------------------------------------------------------------------
// Diagnóstico: registrar TODOS los eventos de teclado/edición/portapapeles
// sobre los campos de la página y validar las reglas del spec (criterio 6).
// ---------------------------------------------------------------------------
const ALLOWED_INPUT_TYPES = new Set([
  "insertText", "insertLineBreak", "insertParagraph", "deleteContentBackward",
]);
const rows = [];
const logTable = document.getElementById("logTable");
// El arnés E2E lee este array (read-only). Se expone a propósito: insertar una
// fila de tabla POR EVENTO saturaba el main thread del renderer en textos de
// 2000+ caracteres (~11.000 eventos) y degradaba TODO lo que corre en la página
// (listeners de Esc, lecturas del campo, foco). Ahora el DOM queda quieto y la
// tabla se renderiza recién al click en "Verificar" (últimas 300 filas).
window.__events = rows;

function record(ev, extra) {
  rows.push({
    type: ev.type,
    isTrusted: ev.isTrusted,
    key: ev.key || null,
    code: ev.code || null,
    keyCode: ev.keyCode || 0,
    inputType: ev.inputType || null,
    data: ev.data === null || ev.data === undefined ? null : ev.data,
    extra: extra || null,
    t: performance.now(),
  });
  if (rows.length > 50000) rows.splice(0, rows.length - 50000);
}

function renderLogTable(maxRows) {
  logTable.innerHTML = "";
  const slice = rows.slice(-maxRows);
  const trh = document.createElement("tr");
  for (const k of ["type", "isTrusted", "key", "code", "keyCode", "inputType", "data", "extra"]) {
    const th = document.createElement("th");
    th.textContent = k;
    trh.appendChild(th);
  }
  logTable.appendChild(trh);
  for (const row of slice) {
    const tr = document.createElement("tr");
    for (const k of ["type", "isTrusted", "key", "code", "keyCode", "inputType", "data", "extra"]) {
      const td = document.createElement("td");
      const v = row[k] === null ? "" : String(row[k]);
      td.textContent = v.length > 40 ? v.slice(0, 40) + "…" : v;
      tr.appendChild(td);
    }
    logTable.appendChild(tr);
  }
}

const FIELDS = [document.getElementById("inp"), document.getElementById("ta"),
                document.getElementById("ce"), document.getElementById("xce"),
                document.getElementById("xce2")];
// Contador de Esc REAL que llega al nivel del campo (fase burbuja): mientras
// TypeClip tipea, el Esc de cancelación debe TRAGARSE en document-captura y
// nunca llegar acá (si no, el sitio lo recibe: p.ej. X abre su diálogo de
// "guardar borrador"). El arnés E2E lo asserta en el bloque F.
window.__escSeen = 0;
for (const f of FIELDS) {
  f.addEventListener("keydown", (e) => {
    if (e.isTrusted && e.key === "Escape") window.__escSeen++;
  });
}
for (const f of FIELDS) {
  for (const type of ["keydown", "keypress", "keyup", "beforeinput", "input", "paste", "copy", "cut", "drop", "dragover"]) {
    f.addEventListener(type, (e) => record(e, f.id), { capture: true });
  }
  // paste también a nivel documento (algunos sitios escuchan ahí)
  document.addEventListener("paste", (e) => {
    if (e.target === f || f.contains(e.target)) record(e, f.id + "/doc");
  }, true);
}

// El input #inp vive dentro de un <form>: el submit (default action de Enter)
// se registra y se cancela — el arnés verifica que TypeClip NUNCA lo dispare.
document.getElementById("inpform").addEventListener("submit", (e) => {
  e.preventDefault();
  record(e, "inpform");
});

// ---------------------------------------------------------------------------
// Composer fake tipo X: bloquea paste y tiene typeahead de menciones.
// Si el texto termina en @token y llega un Enter, se come el Enter
// y "elige" la sugerencia (comportamiento que rompe la verificación naive).
// ---------------------------------------------------------------------------
const xce = document.getElementById("xce");
const pop = document.getElementById("mencionPop");
xce.addEventListener("paste", (e) => { e.preventDefault(); record(e, "XCU-BLOQUEADO"); });
xce.addEventListener("drop", (e) => e.preventDefault());
xce.addEventListener("keyup", () => {
  const t = xce.innerText;
  const m = /(^|\s)@[\w]+$/.exec(t);
  if (m && !t.endsWith("\n")) { pop.style.display = "inline-block"; xce.dataset.typeahead = "1"; }
  else { pop.style.display = "none"; xce.dataset.typeahead = ""; }
});
xce.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && xce.dataset.typeahead === "1") {
    // El typeahead se come el Enter: NO inserta salto de línea.
    e.preventDefault();
    pop.style.display = "none";
    xce.dataset.typeahead = "";
    xce.dataset.mentionEaten = (xce.dataset.mentionEaten || 0) + 1;
    record({ type: "typeahead-ate-enter", isTrusted: true, key: "Enter", code: "Enter", keyCode: 13,
             inputType: null, data: null }, "XCE");
  }
});

// ---------------------------------------------------------------------------
// Editor async (Lexical/ProseMirror-like): cancela el beforeinput y aplica el
// texto 60 ms después. Ejercita la sonda de caracteres especiales: tiene que
// esperar el render diferido en vez de duplicar el caracter con insertText.
// ---------------------------------------------------------------------------
{
  const ed = document.getElementById("xce2");
  ed.addEventListener("beforeinput", (e) => {
    if (e.inputType !== "insertText" || e.data === null) return;
    e.preventDefault();
    const data = e.data;
    setTimeout(() => {
      const sel = document.getSelection();
      if (!sel || !sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      range.deleteContents();
      const node = document.createTextNode(data);
      range.insertNode(node);
      range.setStartAfter(node);
      range.setEndAfter(node);
      sel.removeAllRanges();
      sel.addRange(range);
    }, 60);
  });
}

// ---------------------------------------------------------------------------
// Verificación (criterio 6)
// ---------------------------------------------------------------------------
document.getElementById("verify").addEventListener("click", () => {
  const out = [];
  let fail = 0;
  const check = (cond, msg) => {
    if (cond) out.push('<div class="ok">✓ ' + msg + "</div>");
    else { out.push('<div class="bad">✗ ' + msg + "</div>"); fail++; }
    return cond;
  };

  const ks = rows.filter((r) => r.type === "keydown" || r.type === "keyup");
  const beforeinputs = rows.filter((r) => r.type === "beforeinput");
  const inputs = rows.filter((r) => r.type === "input");
  const pastes = rows.filter((r) => r.type === "paste");
  const drops = rows.filter((r) => r.type === "drop");

  check(ks.length > 0, `keydown/keyup capturados: ${ks.length}`);
  const untrustedKey = ks.filter((r) => !r.isTrusted);
  if (ks.length) check(untrustedKey.length === 0,
    `todos los keydown/keyup con isTrusted=true (${untrustedKey.length} violaciones)`);

  if (inputs.length || beforeinputs.length) {
    const untrustedIn = inputs.filter((r) => !r.isTrusted);
    check(untrustedIn.length === 0,
      `todos los input con isTrusted=true (${untrustedIn.length} violaciones)`);
    const badType = [...beforeinputs, ...inputs].filter((r) => r.inputType && !ALLOWED_INPUT_TYPES.has(r.inputType));
    check(badType.length === 0,
      `inputType solo de la lista permitida (${badType.length} violaciones` +
      (badType.length ? ": " + [...new Set(badType.map((r) => r.inputType))].join(", ") : "") + ")");
    const cp = (s) => Array.from(s).length;
    const multi = [...beforeinputs, ...inputs].filter((r) => r.data !== null && cp(r.data) !== 1);
    check(multi.length === 0,
      `data de un solo code point en beforeinput/input (${multi.length} violaciones` +
      (multi.length ? ": " + JSON.stringify([...new Set(multi.map((r) => r.data))].slice(0, 5)) : "") + ")");
  }
  check(pastes.length === 0, `cero eventos "paste" (${pastes.length})`);
  check(drops.length === 0, `cero eventos "drop" (${drops.length})`);

  const n = (x) => (x ? x : "sin");
  out.push(`<div>Resumen: ${n(ks.length)} teclas, ${n(beforeinputs.length)} beforeinput, ${n(inputs.length)} input, ${pastes.length} paste.</div>`);
  document.getElementById("verifyOut").innerHTML =
    fail === 0 ? '<span class="ok">TODO OK</span>' : '<span class="bad">' + fail + " REGLA(S) VIOLADA(S)</span>";
  document.getElementById("verifyOut").innerHTML += out.join("");
  renderLogTable(300); // solo ahora se toca el DOM
});

document.getElementById("clear").addEventListener("click", () => {
  rows.length = 0;
  logTable.innerHTML = "";
  document.getElementById("verifyOut").textContent = "Log limpio.";
});
