# TypeClip — revisión de políticas CWS antes del envío

Fecha: 2026-11-08 · Versión preparada: 1.3.0 · Rama: `store-readiness`

Matriz política → cumplimiento (con evidencia verificable) → riesgo residual.
Referencia: Chrome Web Store Developer Program Policies
(https://developer.chrome.com/docs/webstore/program-policies/) y la
Developer Dashboard Privacy tab.

## Matriz

| Política CWS | Cumplimiento de TypeClip | Evidencia | Riesgo residual |
|---|---|---|---|
| **Single purpose** | Un solo propósito: tipear el portapapeles en el campo enfocado, por comando explícito. Todo el código sirve a eso (lectura de clipboard, teclado, verificación, opciones de ritmo). | `background.js` (única acción: sesión de tipeo); declaración en `store/listing/en.md` | Bajo |
| **Permisos mínimos** | 6 permisos, cada uno con uso real y acotado; sin `host_permissions`, sin `<all_urls>`. `activeTab` limita al tab invocado. | `tools/audit.py` (evidencia archivo:línea por permiso, sin APIs sin permiso declarado); tabla en `store/listing/en.md` | Bajo |
| **`debugger` en particular** | Se adjunta SOLO durante el tipeo del tab activo invocado por el usuario, se desprende al terminar/cancelar (incluido el race de arranque). Chrome muestra su infobar amarilla todo el tiempo — imposible que pase desapercibido. | Tests E2E F (detach limpio, re-tipeo) y código de attach/detach en `background.js`; nota al revisor en el listing | **Medio**: revisión manual más exigente; posible ronda de preguntas. Mitigación: justificación explícita + demo + código visible en GitHub |
| **No código remoto** | Cero pedidos de red: sin fetch/XHR/WebSocket/sendBeacon/analytics. Todo el código viaja en el paquete. | `tools/audit.py` → TODO OK, exit 0; respuesta "¿código remoto? → No" en el listing | Bajo |
| **No ofuscación / malware** | Código legible, comentado, sin eval/Function/importScripts remotos, sin minificación. | `tools/audit.py` (heurística de minificación y dynamic-eval) | Bajo |
| **User Data Policy + Limited Use** | Datos tocados: texto del portapapeles y contenido del campo, SOLO en memoria, durante la invocación. Nunca transmitidos, guardados ni compartidos. Sync de opciones = settings del usuario vía Chrome. Declaración propuesta: "User-generated content" con venta/uso no relacionado = No. | `PRIVACY.md` + `docs/privacy.html`; `audit.py` (sin storage de texto, sin logging del contenido); sección "Data use" del listing | **Medio-bajo**: la categorización exacta la confirma el dueño en el dashboard (DECISIÓN PENDIENTE si además declarar "Website content") |
| **Comportamiento engañoso / inesperado** | Lo que hace es visible: infobar de Chrome durante el tipeo, badge con progreso, sin acciones ocultas, nunca envía forms ni aprieta botones del sitio. El listing describe exactamente eso (sin prometer "indetectabilidad": término PROHIBIDO en nuestra copia). | Listing EN/ES (reglas de copia honesta aplicadas); tests L (0 submits, 0 Enter en form) | **Medio-bajo**: un revisor puede leer "útil donde bloquean el pegado" como evasión de controles del sitio. La copia lo presenta como tipeo real y visible, con infobar; no promete burlar nada |
| **Spam / keyword stuffing** | Copia del listing sin repetición de keywords (ninguna palabra clave >5 veces), sin listas de marcas ni sitios compatibles. | `store/listing/en.md` + `es.md` | Bajo |
| **Impersonación / marcas de terceros** | Ninguna marca de terceros en nombre, íconos, screenshots o descripción (no se nombran X/Twitter, LinkedIn, etc.). Assets: logo propio "TC". | `store/assets/*` + listings | Bajo |
| **Publicidad** | Sin ads ni monetización alguna. | Código (cero red) + listing | Bajo |
| **Funcionalidad mínima** | La UI es una página de opciones + badge; sin popup vacío ni promesas de UI sin función. | `options.html` funcional; `manifest.json` sin default_popup | Bajo |
| **Metadata consistente** | Nombre/descripción idénticos entre manifest (`__MSG_*__`), listings EN/ES, README y política de privacidad. | `_locales/en|es/messages.json` ↔ `store/listing/*.md` ↔ `PRIVACY.md` | Bajo |

## Notas de riesgo que NO se pueden eliminar desde el código

1. **Permiso `debugger`**: es el permiso de mayor escrutinio de la tienda.
   Chrome lo marca para revisión manual. No hay alternativa para generar
   eventos de teclado reales por tab. La extensión es honesta al respecto
   (infobar visible, detach inmediato, código visible en GitHub con E2E que lo prueba).
   Expectativa realista: posible rechazo o ronda de aclaraciones antes de la
   aprobación.

2. **Framing "campos que bloquean el pegado"**: está en el listing porque es
   la utilidad real, verificable en los tests (ningún evento paste). La copia
   evita prometer evasión de detección: describe eventos de teclado reales y
   visibles, con el cartel de Chrome a la vista.

3. **Chrome 155 y el debugger en perfiles gestionados**: hay comentarios
   públicos de que Chrome planea restringir `chrome.debugger` en perfiles
   administrados. NO confirmado en las release notes oficiales que
   consultamos → documentado en el README como no confirmado. No afecta al
   envío (los usuarios normales no están en perfil gestionado), pero conviene
   saberlo antes de prometer soporte a empresas.

4. **A confirmar en el dashboard** (no verificable fuera de él):
   - Monto del pago único de registro de desarrollador.
   - Requisito/flujo de 2FA de la cuenta.
   - Set exacto de categorías de datos del tab de privacidad y el texto de
     cada pregunta de "uso de datos".

## Decisión pendiente del dueño (NO tomar por cuenta propia)

- ~~**Licencia del repo**~~ — RESUELTA (2026-11-08): GPLv2, archivo `LICENSE`
  en la raíz. El listing y la política de datos siguen sin afirmar nada sobre
  licencia (correcto: el dashboard no lo pide).
- **Declarar o no "Website content"** además de "User-generated content"
  (lectura del campo para verificar, en memoria). Recomendación del análisis:
  declarar también "Website content" es la opción conservadora.
- **Habilitar GitHub Pages sobre `/docs`** para las URLs
  `pablopeu.github.io/typeclip/{privacy,demo}.html` (si no, usar como
  fallback el link a `PRIVACY.md` en el listing).
