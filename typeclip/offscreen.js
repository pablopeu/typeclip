// TypeClip — offscreen.js
// Corre en el offscreen document de la extensión (NO en la página del sitio).
// Única función: leer el texto del portapapeles del sistema y devolverlo al service worker.
// El execCommand("paste") de acá es la única excepción permitida a la regla
// anti-paste: corre en una página de la extensión, el sitio nunca lo ve.
//
// Nota: el texto vive solo en memoria. No se loguea, no se guarda, no sale por red.

const buf = document.getElementById("buf");

async function readClipboard() {
  // 1) Intento con la Async Clipboard API (si el documento está "focused" alcanza).
  try {
    const t = await navigator.clipboard.readText();
    if (t !== null && t !== undefined) return { ok: true, text: t };
  } catch (e) {
    // Sin foco/permiso: caemos al camino clásico de abajo.
  }
  // 2) Camino clásico: focus al textarea y execCommand("paste").
  buf.value = "";
  buf.focus();
  buf.select();
  const ok = document.execCommand("paste");
  const text = buf.value;
  buf.value = "";
  buf.blur();
  if (ok || text) return { ok: true, text };
  return { ok: false, error: "execCommand(paste) devolvió vacío (¿portapapeles sin texto?)" };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.tc === "read-clipboard") {
    readClipboard().then(sendResponse);
    return true; // respuesta asincrónica
  }
});
