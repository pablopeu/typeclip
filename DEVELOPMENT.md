# TypeClip — notas de desarrollo

Extensión Chrome MV3, sin dependencias ni paso de build. Para el uso cotidiano,
ver el [README](README.md).

## Arquitectura

| Archivo | Rol |
|---|---|
| `typeclip/manifest.json` | MV3; permisos: `debugger`, `clipboardRead`, `offscreen`, `activeTab`, `scripting`, `storage`. Sin permisos de hosts. Comando `type-clipboard` (Alt+Shift+V). `minimum_chrome_version` 116 (offscreen completo; las APIs viejas se usan con guard igual). |
| `typeclip/background.js` | Service worker orquestador: validaciones, lectura del portapapeles (offscreen), armado del plan de tipeo, sesión `chrome.debugger` (CDP), cancelación/abort, badge y verificación final. |
| `typeclip/offscreen.{html,js}` | Documento offscreen (razón `CLIPBOARD`): lee el portapapeles con `execCommand("paste")` — en MV3 el SW no puede tocar el clipboard. |
| `typeclip/content.js` | Se inyecta on-demand (no declarativo): detecta el elemento editable con foco (`input`/`textarea`/`contenteditable`), monitorea Esc/foco, ejecuta los planes de los fallbacks y lee el campo para verificar. |
| `typeclip/options.{html,js}` | Configuración en `chrome.storage.sync`. Página bilingüe (ver abajo) con footer de redes estilo byd.peu.net. |
| `typeclip/test/` | Página de prueba (campos + diagnóstico de eventos). Sirve para prueba manual y la usa el arnés E2E. |
| `tools/` | Arnés de pruebas e iconos (Python + Playwright). |

## Flujo de una invocación

1. Guardas de regla B: ventana enfocada, pestaña activa y visible, URL operable
   (chrome:// etc. → `ERR`).
2. Inyección de `content.js` en todos los frames (`allFrames`); el frame cuyo
   foco es un campo editable responde con `ok` + `kind` (input / textarea /
   contenteditable). Si la inyección falla porque ya está cargado (página de
   prueba), se sondea por mensaje.
3. Lectura del portapapeles **en ese momento**, vía offscreen. El texto vive
   solo en memoria: nunca se loguea, guarda o envía.
4. **Inputs de una sola línea** (`kind === "input"`): los `\n` se colapsan a un
   espacio **antes** de armar el plan. Un Enter real en un `<input>` dispara el
   default action de Chrome (submit del `<form>` + `change`) — verificado
   empíricamente; la regla "nunca hace submit" lo prohíbe.
5. `buildPlan`: iteración por code points (nunca code units). Pasos `char`
   (keyDown/keyUp CDP con `text`, Shift como evento real: Shift↓ tecla↓ tecla↑
   Shift↑), `enter`, `bs` (corrección de typos). Tab → espacios configurables
   (un Tab real movería el foco). Pares surrogate (emoji) → `Input.insertText`
   de un code point.
6. **Caracteres fuera del layout US** (ñ, á, ¿…): la primera aparición de cada
   uno se verifica en vivo comparando el LARGO del campo antes y después del
   keyDown (mirar la cola asumía caret al final y duplicaba el caracter con el
   caret en el medio), esperando hasta ~150 ms para editores que insertan
   async (Lexical, ProseMirror). Si no creció, ese code point pasa a
   insertText (fallback puntual, permanente por sesión).
7. Sesión CDP con `chrome.debugger` + `Input.dispatchKeyEvent`. Si el attach
   falla → **fallback JS** (content script: keydown/keypress sintéticos +
   `execCommand("insertText")`, un code point por evento — sin beforeinput
   sintético: van solo los nativos de execCommand, y duplicarlo insertaba dos
   veces en editores que hacen preventDefault); si execCommand tampoco →
   **fallback setter** (setter nativo de `value`/`textContent` + evento
   `input` manual con `inputType: "insertText"`, `data` de un code point).
   El método usado queda en el tooltip del badge (CDP / JS / JS/SET).
8. Verificación final: lee el campo, normaliza (NFC, saltos uniformes,
   espacios de relleno, trim) y compara → badge `OK` / `DIF` (con detalle de
   la primera diferencia) / `ERR`. Con línea base: si el campo YA tenía texto
   (leído antes de tipear), `OK` también acepta "el texto quedó contenido en
   el campo" (el caret pudo estar en cualquier posición).
9. Cancelación: Esc (keydown → content script → mensaje `esc` con guard de
   sender; mientras hay sesión el Esc se TRAGA con preventDefault +
   stopImmediatePropagation en document-captura, para que el sitio no lo
   procese — p.ej. X abriría "guardar borrador"), re-invocación (toggle),
   cambio de pestaña/ventana (abort con detach). El abort marca `ERR` con el
   motivo; la cancelación deja badge limpio.

Detalles de robustez del CDP:

- `Input.dispatchKeyEvent` se envía SIN `timestamp`: CDP lo espera en segundos
  desde epoch y un `Date.now()` en ms dejaba el `event.timeStamp` del sitio
  ~1.7e15 ms a futuro (medido; test M). Sin el campo, Chrome estampa "ahora".
- `cancel()` durante el arranque (lectura de clipboard / attach): `runSession`
  re-chequea `session` después de cada await y suelta el debugger él mismo si
  había llegado a attachear (quedaba colgado con el infobar).

## Humanización

Delays log-normales alrededor de la velocidad base (WPM), jitter, pausas extra
tras espacio/puntuación/salto, pausas "de pensar" ocasionales y typos
opcionales (tecla vecina QWERTY → pausa → Backspace → tecla correcta). **La
misma lógica está duplicada en `background.js` y `content.js`** (el fallback
corre dentro de la página): mantener las dos copias sincronizadas.

## Página de opciones: idiomas y footer

El HTML está autorizado en **inglés** (el idioma por defecto, así no hay flash
de otro idioma al abrir). `options.js` tiene el diccionario `STRINGS` y
`applyLang()` reemplaza el texto de cada elemento con `data-i18n`; la elección
del selector se guarda en `chrome.storage.sync` (clave `uiLang`) y se recuerda
al recargar. No se usa `chrome.i18n`/`_locales` porque seguiría al locale del
navegador: acá el selector es explícito y recordado. El footer (una línea:
texto + 5 redes + botón PEU.NET, diseño tomado de byd.peu.net) también se
traduce y sigue el idioma activo.

Los íconos (barra de extensiones, manifest y el logo de 32px del título) se
generan con `tools/make_icons.py` a partir de `TC.png` del raíz (square-pad
sobre su propio fondo + LANCZOS).

## Invariantes (verificados por el arnés)

- Cero eventos `paste`/`drop`; nunca `DataTransfer`.
- Máximo **un code point por evento** `beforeinput`/`input`.
- `inputType` solo de: `insertText`, `insertLineBreak`, `insertParagraph`,
  `deleteContentBackward`.
- Solo la pestaña activa con ventana enfocada; una acción explícita por tipeo.
- Nunca submit de formularios (incluido el caso input single-line + payload
  multi-línea, test L).
- Nunca cambia el foco ni hace click; el texto del portapapeles nunca sale de
  memoria.

## Suite E2E (`tools/e2e.py`)

32/32 PASS (Chromium 156 headless, Playwright 1.64). Cobertura: A input +
eventos trusted, B textarea 280+ (tildes/ñ/¿¡/emoji/@), C contenteditable,
D composer fake tipo X (typeahead se come el Enter → DIF esperado), E 2000+
caracteres de corrido (ciclo de vida del SW), F cancelación por Esc / toggle /
re-tipeo tras detach / Esc tragado sin llegar al sitio, G chrome:// rechazado,
H abort por cambio de pestaña, I typos autocorregidos, J fallback JS forzado
(+ 1 beforeinput nativo por input), K fallback setter forzado, L input en
form multi-línea sin submit, M timeStamp de los eventos CDP coherente con
performance.now(), N campo con texto previo (badge OK contra línea base),
O caret en el medio sin duplicar ñ ¿ ¡ é, P editor async (inserta 60 ms
después) sin duplicar especiales.

Ejecución: `python3 tools/e2e.py` (levanta la página de prueba en
`0.0.0.0:8737` y lanza Chromium con la extensión cargada).

Notas del arnés que costaron descubrir (headless nuevo):

- `channel="chromium"` (build completo); el headless shell no soporta
  extensiones y el Chrome de marca ignora `--load-extension`.
- Los comandos de extensión no se disparan con teclas sintéticas: el arnés
  llama `invoke()` directo en el service worker.
- Con `chrome.debugger` adjunto, **todo** el tráfico CDP de Playwright hacia
  esa pestaña se encola detrás de los comandos del tipeo (los eval del arnés no
  corren hasta el detach). Para cancelar mid-tipeo se despacha un Esc confiable
  vía la propia sesión de debugger de la extensión; para el cambio de pestaña
  se usa `chrome.tabs.update` desde el SW (nivel browser).
- Timeouts con `time.sleep()` de Python, no timers de la página (mismo
  encolamiento).

Otros scripts de `tools/`: `smoke.py` (carga mínima), `make_icons.py`
(regenera los PNG desde `TC.png`), `e_diag.py` / `esc_diag*.py`
(reproducciones forenses de los bugs de cancelación, quedan como referencia).

## Verificación manual pendiente

Lo que no se puede simular headless: el infobar de "software de depuración"
visible, el atajo real Alt+Shift+V, el **click en el ícono de la barra** (que
pasa por la UI del browser y puede desenfocar el documento — verificar en un
sitio real que tipea igual que con el atajo), y los sitios reales (X, Gmail)
con login propio.
