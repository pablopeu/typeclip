// TypeClip — options.js: página de opciones bilingüe (inglés por defecto,
// selector a español cuya elección se recuerda en chrome.storage.sync) y
// carga/guarda de la configuración del tipeo.

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

// Textos de la interfaz. El HTML viene en inglés (idioma por defecto);
// applyLang() reemplaza el texto de cada elemento con data-i18n.
const STRINGS = {
  en: {
    docTitle: "TypeClip — options",
    h1rest: "— options",
    fSpeed: "Speed",
    lWpm: "Base speed:", lWpmUnit: "WPM (words per minute)",
    lJitter: "Human variation (jitter):",
    lPauses: "Extra pauses (longer after spaces, punctuation and line breaks)",
    lThink: "Occasional “thinking” pause:", lThinkUnit: "% of characters",
    fTypos: "Typing mistakes",
    lTypos: "Simulate mistakes (neighboring QWERTY key + Backspace to correct)",
    lTypoPct: "Mistake probability per character:",
    fSpecial: "Special characters",
    lTabs: "Tab characters in the text:",
    optSpaces: "Replace with spaces (a real Tab would move the focus)",
    optSkip: "Skip",
    lTabN: "Spaces per Tab:",
    fShortcut: "Keyboard shortcut",
    lSc1: "The default shortcut is",
    lSc2: "(Ctrl+Shift+V clashes with “paste without formatting”). To change it:",
    btnShortcuts: "open chrome://extensions/shortcuts",
    btnSave: "Save", saved: "Saved ✓",
    privacy1: "The typed text is never stored nor sent anywhere. These options are saved in",
    footTitle: "Do you like knives? Follow me on my socials",
  },
  es: {
    docTitle: "TypeClip — opciones",
    h1rest: "— opciones",
    fSpeed: "Velocidad",
    lWpm: "Velocidad base:", lWpmUnit: "WPM (palabras por minuto)",
    lJitter: "Variación humana (jitter):",
    lPauses: "Pausas extra (más largo tras espacios, puntuación y saltos de línea)",
    lThink: "Pausa de “pensar” ocasional:", lThinkUnit: "% de los caracteres",
    fTypos: "Errores de tipeo",
    lTypos: "Simular errores (tecla vecina del QWERTY + Backspace para corregir)",
    lTypoPct: "Probabilidad de error por caracter:",
    fSpecial: "Caracteres especiales",
    lTabs: "Tabulaciones del texto:",
    optSpaces: "Reemplazar por espacios (un Tab real movería el foco)",
    optSkip: "Omitir",
    lTabN: "Cantidad de espacios por Tab:",
    fShortcut: "Atajo de teclado",
    lSc1: "El atajo por defecto es",
    lSc2: "(Ctrl+Shift+V choca con “pegar sin formato”). Para cambiarlo:",
    btnShortcuts: "abrir chrome://extensions/shortcuts",
    btnSave: "Guardar", saved: "Guardado ✓",
    privacy1: "El texto tipeado nunca se guarda ni se envía a ningún lado. Estas opciones se guardan en",
    footTitle: "¿Te gustan los cuchillos? Seguime en mis redes",
  },
};

const $ = (id) => document.getElementById(id);
let uiLang = "en";

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

// Idioma: aplicar textos, marcar el selector y recordar la elección.
function applyLang(lang) {
  uiLang = STRINGS[lang] ? lang : "en";
  const t = STRINGS[uiLang];
  document.documentElement.lang = uiLang;
  document.title = t.docTitle;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const key = el.dataset.i18n;
    if (key in t) el.textContent = t[key];
  }
  $("langEn").setAttribute("aria-pressed", String(uiLang === "en"));
  $("langEs").setAttribute("aria-pressed", String(uiLang === "es"));
}
for (const [id, lang] of [["langEn", "en"], ["langEs", "es"]]) {
  $(id).addEventListener("click", () => {
    applyLang(lang);
    chrome.storage.sync.set({ uiLang: lang });
  });
}

// Abrir la página de atajos de chrome:// (los links <a> a chrome:// no se
// pueden usar desde una página de extensión; tabs.create sí puede, y sin
// handler inline: la CSP de las páginas MV3 bloquea onclick="…").
$("openShortcuts").addEventListener("click", () => {
  chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
});

$("save").addEventListener("click", () => {
  chrome.storage.sync.set({ settings: readForm() }, () => {
    $("status").textContent = STRINGS[uiLang].saved;
    setTimeout(() => ($("status").textContent = ""), 1500);
  });
});

chrome.storage.sync.get({ settings: {}, uiLang: "en" }, ({ settings, uiLang: savedLang }) => {
  applyLang(savedLang);
  writeForm({ ...DEFAULTS, ...settings });
});
