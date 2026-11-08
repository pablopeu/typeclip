# TypeClip — Privacy Policy / Política de privacidad

## English

**Last updated: 2026-11-08.**

TypeClip is a Chrome extension that types the text you copied into the field
you choose, key by key. This page explains, in plain terms, exactly what it
does with your data.

### What TypeClip reads

- The **text of your clipboard**, and only at the exact moment you run TypeClip
  (keyboard shortcut or toolbar click). It is held **in memory only**, used to
  type it, and discarded. It is never written to disk.
- The **current content of the field** you point it at, to verify the result
  (and to know what was already there before typing). Also memory-only.

### What TypeClip stores

- **Your options only** (typing speed, language of the options page, etc.) in
  `chrome.storage.sync`. That storage is provided and synced by Chrome with
  your Google account — TypeClip has no servers and cannot read anything else
  from it. If you remove the extension, the stored options go with it.

### What TypeClip never does

- **Never transmits anything.** No network requests of any kind: no fetch, no
  XHR, no WebSockets, no analytics, no telemetry.
- **Never stores the typed text** — not locally, not anywhere.
- **Never shares data with third parties.** There are no third parties.
- **No remote code.** Everything that runs ships inside the extension package
  and can be inspected in the source repository.

### The "debugger" permission

TypeClip uses Chrome's debugger protocol to send **real keyboard events** to
the field, which is what makes sites accept the text as typing. While it
types, Chrome shows a yellow banner ("Chrome is being controlled by automated
test software"). That banner is Chrome being transparent with you; TypeClip
detaches the debugger the moment typing ends (or when you cancel with Esc)
and the banner disappears.

### Contact

Questions or issues: [github.com/pablopeu/typeclip/issues](https://github.com/pablopeu/typeclip/issues).

The use of information adheres to the Chrome Web Store User Data Policy,
including the Limited Use requirements.

---

## Español

**Última actualización: 2026-11-08.**

TypeClip es una extensión de Chrome que tipea, letra por letra, el texto que
copiaste en el campo que elijas. Esta página explica en claro exactamente qué
hace con tus datos.

### Qué lee TypeClip

- El **texto de tu portapapeles**, únicamente en el momento exacto en que
  ejecutás TypeClip (atajo o click en el ícono). Vive **solo en memoria**,
  se usa para tipearlo y se descarta. Nunca se escribe a disco.
- El **contenido actual del campo** al que lo apuntás, para verificar el
  resultado (y saber qué había antes de tipear). También solo en memoria.

### Qué guarda TypeClip

- **Solo tus opciones** (velocidad, idioma de la página de opciones, etc.) en
  `chrome.storage.sync`. Ese almacenamiento lo provee y sincroniza Chrome con
  tu cuenta de Google — TypeClip no tiene servidores y nada más puede leer de
  ahí. Si desinstalás la extensión, las opciones se van con ella.

### Qué nunca hace TypeClip

- **Nunca transmite nada.** Cero pedidos de red: sin fetch, sin XHR, sin
  WebSockets, sin analítica, sin telemetría.
- **Nunca guarda el texto tipeado** — ni localmente ni en ningún lado.
- **Nunca comparte datos con terceros.** No hay terceros.
- **Sin código remoto.** Todo lo que corre viene adentro del paquete de la
  extensión y se puede inspeccionar en el repositorio.

### El permiso "debugger"

TypeClip usa el protocolo de depuración de Chrome para enviar **eventos de
teclado reales** al campo, que es lo que hace que los sitios acepten el texto
como tipeo. Mientras tipea, Chrome muestra un cartel amarillo ("Chrome está
siendo controlado por un software de depuración"). Ese cartel es Chrome siendo
transparente con vos; TypeClip desprende el debugger en el instante en que
termina el tipeo (o cuando cancelás con Esc) y el cartel desaparece.

### Contacto

Preguntas o problemas: [github.com/pablopeu/typeclip/issues](https://github.com/pablopeu/typeclip/issues).

El uso de la información se adhiere a la Política de Datos de Usuario de la
Chrome Web Store, incluyendo los requisitos de Uso Limitado (Limited Use).
