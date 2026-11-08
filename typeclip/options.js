// TypeClip — options.js: carga/guarda la configuración en chrome.storage.sync.

// Valores por defecto (los mismos que usa background.js al arrancar).
const DEFAULTS = {
  wpm: 100,        // velocidad base en palabras por minuto (40–250)
  jitter: 50,      // variación humana en % (10–100)
  pauses: true,    // pausas extra tras espacio/puntuación/salto de línea
  thinkPct: 2,     // probabilidad de pausa de "pensar" en % (0–10)
  typos: false,    // simular errores de tipeo (default OFF)
  typoPct: 1.5,    // probabilidad de error por caracter en % (0–5)
  tabMode: "spaces", // qué hacer con Tabs (un Tab real movería el foco)
  tabSpaces: 4,    // espacios por Tab si tabMode = spaces
};

const $ = (id) => document.getElementById(id);

function clamp(v, lo, hi, dflt) {
  v = Number(v);
  if (!Number.isFinite(v)) return dflt;
  return Math.min(hi, Math.max(lo, v));
}

function readForm() {
  return {
    wpm: clamp($("wpm").value, 40, 250, DEFAULTS.wpm),
    jitter: clamp($("jitter").value, 10, 100, DEFAULTS.jitter),
    pauses: $("pauses").checked,
    thinkPct: clamp($("thinkPct").value, 0, 10, DEFAULTS.thinkPct),
    typos: $("typos").checked,
    typoPct: clamp($("typoPct").value, 0, 5, DEFAULTS.typoPct),
    tabMode: $("tabMode").value === "skip" ? "skip" : "spaces",
    tabSpaces: clamp($("tabSpaces").value, 1, 8, DEFAULTS.tabSpaces),
  };
}

function writeForm(s) {
  $("wpm").value = s.wpm; $("wpmVal").textContent = s.wpm;
  $("jitter").value = s.jitter; $("jitterVal").textContent = s.jitter;
  $("pauses").checked = s.pauses;
  $("thinkPct").value = s.thinkPct; $("thinkVal").textContent = s.thinkPct;
  $("typos").checked = s.typos;
  $("typoPct").value = s.typoPct; $("typoVal").textContent = s.typoPct;
  $("tabMode").value = s.tabMode;
  $("tabSpaces").value = s.tabSpaces; $("tabVal").textContent = s.tabSpaces;
  syncTypoRow();
}

function syncTypoRow() {
  $("typoRow").classList.toggle("disabled", !$("typos").checked);
}

// Etiquetas vivas de los sliders.
for (const [id, valId] of [["wpm", "wpmVal"], ["jitter", "jitterVal"], ["thinkPct", "thinkVal"], ["typoPct", "typoVal"], ["tabSpaces", "tabVal"]]) {
  $(id).addEventListener("input", () => { $(valId).textContent = $(id).value; });
}
$("typos").addEventListener("change", syncTypoRow);

$("save").addEventListener("click", () => {
  chrome.storage.sync.set({ settings: readForm() }, () => {
    $("status").textContent = "Guardado ✓";
    setTimeout(() => ($("status").textContent = ""), 1500);
  });
});

chrome.storage.sync.get({ settings: {} }, ({ settings }) => writeForm({ ...DEFAULTS, ...settings }));
