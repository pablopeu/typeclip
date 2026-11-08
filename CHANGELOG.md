# Changelog

Formato simple: lo importante de cada versión, más abajo los detalles en el
git log.

## 1.3.0 (no publicada aún — rama `store-readiness`)

Preparación para el envío a la Chrome Web Store (sin cambios de comportamiento
del motor de tipeo):

- Verificación final más honesta: con el campo precargado, `OK` solo si el
  texto del portapapeles aparece **más veces** que en la línea base (el
  "contains" anterior daba un OK falso en un campo congelado precargado con
  el texto exacto). Tests E2E nuevos Q y R.
- Robustez medida empíricamente: timeout de 15 s en los comandos CDP y de 2 s
  en las lecturas de la sonda (un editor que muta el DOM en su handler de
  input puede trabar el renderer y dejar un `dispatchKeyEvent` sin respuesta
  para siempre — ahora aborta, desprende el debugger y marca ERR); limpieza
  al renacer el SW de attaches huérfanos (si Chrome mata el SW a mitad de
  sesión, el cartel amarillo quedaba puesto para siempre y el badge clavado).
  Test E2E S (renderer trabado → ERR).
- Suite E2E: 37/37 (antes 32/32).
- Internacionalización de la extensión: `_locales/en` + `_locales/es`,
  `default_locale: en`, strings del manifest (nombre/descripción/título del
  ícono/comando) vía `__MSG_…__` y mensajes en runtime (badges y tooltips)
  vía `chrome.i18n`. La página de opciones mantiene su selector EN/ES propio.
- Nueva documentación: `PRIVACY.md` (política de privacidad, EN+ES),
  `docs/privacy.html`, `docs/demo.html` (página de demo para el revisor),
  fichas de la tienda (`store/`), revisión de políticas y checklist de envío.
- Herramientas: `tools/audit.py` (auditoría estática: permisos, red, CSP,
  logging de contenido del portapapeles), `tools/store_assets.py` (assets de
  la tienda), `tools/package.py` (ZIP de envío con validaciones).

## 1.2.0

Fixes de una revisión externa del motor de tipeo:

- `timestamp` de los eventos CDP: CDP espera segundos-epoch, se enviaban
  milisegundos → los `event.timeStamp` del sitio quedaban ~1.7e15 ms a futuro
  (test M).
- Sonda de caracteres especiales por longitud antes/después (la sonda vieja
  miraba la cola del campo y duplicaba ñ/¿/¡/é con el caret en el medio;
  ahora además espera hasta 150 ms por editores async tipo Lexical) (tests
  O y P).
- Race de arranque: si la sesión se cancelaba mientras el debugger se estaba
  adjuntando, quedaba colgado un attach y los monitores globales activos.
- El Esc de cancelación ahora se traga (no llega al sitio mientras TypeClip
  tipea).
- Fallback JS: fuera el `beforeinput` sintético (duplicaba en editores que
  hacen preventDefault); queda el nativo de execCommand.
- `minimum_chrome_version: 116`. Suite E2E 32/32.

## 1.1.0

- Logo propio (monograma TC) en todos los tamaños y README.
- Página de opciones bilingüe (inglés por defecto, selector Español que
  recuerda la elección).
- Footer de redes en el README.

## 1.0.1

- Quitado un handler inline de la página de Opciones (violación de CSP de
  página en MV3).

## 1.0.0

- Versión inicial: tipea el portapapeles caracter a caracter con eventos de
  teclado reales (chrome.debugger/CDP), fallbacks JS y setter, ritmo humano,
  typos simulados, badge OK/DIF/ERR, cancelación por Esc/re-invocación,
  opciones sincronizadas.
