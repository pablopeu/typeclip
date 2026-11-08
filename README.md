# TypeClip

<p align="center"><img src="TC.png" width="120" alt="TypeClip" title="TypeClip"></p>

**English** · [Español](#español)

---

## English

A Chrome extension that **types for you** the text you copied.

Copy it as usual (Ctrl+C), click the field where you want it (an X/Twitter post
box, a form, an email…) and TypeClip writes it **character by character, with
human-like timing**, as if you were typing it yourself. The website sees real
typing: there is no "paste" to block or detect.

### Installation

You need a computer with **Google Chrome** (it doesn't work on phones or in
other browsers).

1. Download the ZIP from the [latest release](https://github.com/pablopeu/typeclip/releases)
   (the **TypeClip-v…zip** button) and unzip it into a folder you won't delete
   (for example `Documents/TypeClip`).
   - If you know git, you can also clone the repository.
2. Open Chrome and type in the address bar: `chrome://extensions` (then Enter).
3. Top right, turn on the **Developer mode** switch.
4. New buttons appear at the top left: click **Load unpacked**.
5. Select the **`typeclip`** folder (the one inside what you unzipped, which
   contains the icons and the extension files).
6. Done: the TypeClip icon (the TC monogram: a white T inside an orange C)
   appears in the extensions
   bar. It's worth **pinning it** (click the puzzle piece 🧩 and then the pin 📌
   on TypeClip's icon) to keep it at hand.

> Important: don't delete or move that folder afterwards — Chrome needs it for
> the extension to keep working.

### How to use it

1. **Copy** the text you want typed (select it and Ctrl+C, as always).
2. **Click the field** where you want it to appear (the cursor should be
   blinking there).
3. Run TypeClip:
   - with the shortcut **Alt + Shift + V**, or
   - with a **click on the TypeClip icon**.
4. Watch it type on its own. The icon shows the progress (`37%`, `68%`…).

Typing respects line breaks, accents, ñ, ¿¡ and emojis. The text is read from
the clipboard **at the moment** you run the extension: if you copy something
else afterwards, what gets typed doesn't change.

#### Canceling mid-way

- Press **Esc**, or
- run the shortcut again (Alt + Shift + V).

It stops immediately and whatever was already typed stays as is (nothing gets
deleted).

### What the letters on the icon mean

| Letter | Color | Meaning |
|---|---|---|
| `37%` | blue | It's typing. |
| **OK** | green | Finished, and the field **matches** what you copied. |
| **DIF** | orange | Finished, but the field **didn't end up exact** (see below). |
| **ERR** | red | It didn't start, or it was cut off. Hover the icon to see why. |

To see the detail behind OK/DIF/ERR, leave the mouse over the icon for a
second.

If the field already had text before you ran TypeClip, **OK** means the typed
text landed inside it (the whole field can't match what you copied).

#### Why can DIF happen?

The text ended up different from what you copied, almost always because
**the page itself** did something, not the extension:

- **X/Twitter mentions**: if a line ends in an `@mention` followed by a line
  break, X's suggestion popup can "eat" that Enter to pick the suggestion.
  Check the text and add the missing break by hand.
- Autocorrect or autocomplete on the site.
- The field's character limit (the text gets cut off at the maximum).

In any case, **review before posting**.

### The yellow "debugging" banner (it's normal)

While it types, Chrome shows a notice at the top: *"Chrome is being controlled
by automated test software"*. **That's expected, and it goes away on its own**
when typing finishes. It's the price of the keyboard events being real (the
genuinely real kind, not simulated).

Two things to know:

- **You don't need to click "Cancel"** on that banner: leave it be, it
  disappears on its own.
- If you cancel it mid-typing, typing stops cleanly (nothing weird is left
  written).

### Settings (optional)

Right-click the icon → **Options**. The page opens in English by default: tap
**Español** (top right) to switch — it remembers your choice. Everything is
saved automatically (it syncs with your Chrome account):

- **Base speed**: how fast it types (from slow to fast).
- **Human variation**: makes the pauses between keys uneven (more natural).
- **Extra pauses**: slightly longer breaks after spaces, periods and line
  breaks.
- **"Thinking" pauses**: every now and then it stops for a moment, "thinking".
- **Typing mistakes** (off by default): occasionally hits a wrong key and fixes
  it with Backspace, like a person would.
- **Tabs**: tabs in the text are replaced with spaces (a real Tab would move
  the cursor to the next field and ruin the typing).

#### Changing the shortcut

If Alt + Shift + V clashes with something: `chrome://extensions/shortcuts` →
find TypeClip → click the pencil and press your preferred combination. On
Windows with two or more keyboard layouts, Alt+Shift is the system's "switch
language" combination and can get in the way — if that happens, pick a
Ctrl-based combination.

### Frequently asked questions

**Does my text go anywhere? Is it stored?**
No. It's read from the clipboard, typed, and discarded. Not saved, not sent, no
server, no permissions to read any website.

**Could it ever post/send on its own?**
Never. TypeClip only writes into the field; the Post/Send button remains yours
to press.

**I pressed the shortcut and nothing happens.**
- Is the cursor blinking in a text field? Click into the field and try again.
- Is the Chrome window the active one? If another application has the focus,
  TypeClip refuses (you'll see `ERR`).
- Did you install the folder properly and not move it? Check step 5 of the
  installation.
- Did you configure a different shortcut? Check at
  `chrome://extensions/shortcuts`.

**Does it work in Gmail / X / forms?**
Yes, in any editable text field on a web page. For sites with their own pop-up
editors (X's composer, Gmail's compose window), results may vary depending on
what the site does with each key; watch the final badge (OK/DIF).

**What about phones?**
No: Chrome extensions don't exist on Android/iOS.

---

For technical details (architecture, typing methods, privacy rules and the
automated test suite), see [DEVELOPMENT.md](DEVELOPMENT.md) (in Spanish).

---

## Español

[English](#english) · **Español**

Extensión de Chrome que **tipea por vos** el texto que copiaste.

La copiás normal (Ctrl+C), hacé click en el campo donde la querés (el cuadro de
texto de X/Twitter, un formulario, un mail…) y TypeClip la escribe **letra por
letra, con tiempos humanos**, como si la escribiras con el teclado. El sitio web
ve tipeo de verdad: no hay "pegado" que bloquear ni detectar.

### Instalación

Necesitás una computadora con **Google Chrome** (no sirve en el celular ni en
otros navegadores).

1. Descargá el ZIP del [último release](https://github.com/pablopeu/typeclip/releases)
   (botón **TypeClip-v…zip**) y descomprimilo en una carpeta que no vayas a
   borrar (por ejemplo `Documentos/TypeClip`).
   - Si sabés usar git, también podés clonar el repositorio.
2. Abrí Chrome y escribí en la barra de direcciones: `chrome://extensions`
   (y Enter).
3. Arriba a la derecha, activá la palanca **Modo de desarrollador**.
4. Aparecen botones nuevos arriba a la izquierda: hacé click en **Cargar
   descomprimida**.
5. Seleccioná la carpeta **`typeclip`** (la que está adentro de lo que
   descomprimiste, que contiene los íconos y los archivos de la extensión).
6. Listo: el ícono de TypeClip (el monograma TC: una T blanca dentro de una C
   naranja) aparece en la barra de
   extensiones. Conviene **fijarlo** (click en la piezita de rompecabezas 🧩 y
   en la chincheta 📌 del ícono de TypeClip) para tenerlo a mano.

> Importante: no borres ni muevas la carpeta después de instalarla — Chrome la
> necesita para que la extensión siga funcionando.

### Cómo se usa

1. **Copiá** el texto que querés tipear (seleccionás y Ctrl+C, como siempre).
2. Hacé **click en el campo** donde querés que aparezca (que quede el cursor
   parpadeando ahí).
3. Ejecutá TypeClip:
   - con el atajo **Alt + Shift + V**, o
   - con un **click en el ícono** de TypeClip.
4. Mirá cómo tipea solo. En el ícono vas viendo el avance (`37%`, `68%`…).

El tipeo respeta saltos de línea, tildes, ñ, ¿¡ y emojis. El texto se lee del
portapapeles **en el momento** en que ejecutás la extensión: si copiás otra cosa
después, no cambia lo que se tipea.

#### Cancelar a mitad

- Apretá **Esc**, o
- volvé a ejecutar el atajo (Alt + Shift + V).

Se corta en el acto y queda lo que ya se tipeó (sin borrar nada).

### Qué significan las letras del ícono

| Letra | Color | Significado |
|---|---|---|
| `37%` | azul | Está tipeando. |
| **OK** | verde | Terminó y el texto del campo **coincide** con lo copiado. |
| **DIF** | naranja | Terminó, pero el campo **no quedó exacto** (ver abajo). |
| **ERR** | rojo | No arrancó o se cortó. Pasá el mouse por el ícono para ver el motivo. |

Para ver el detalle de OK/DIF/ERR, dejá el mouse un segundo sobre el ícono.

Si el campo ya tenía texto antes de ejecutar TypeClip, **OK** significa que el
tipeo quedó insertado adentro (el campo entero no puede coincidir con lo
copiado).

#### ¿Por qué puede salir DIF?

El texto quedó distinto a lo copiado, casi siempre por algo que hizo **la propia
página**, no por la extensión:

- **Menciones de X/Twitter**: si una línea termina en una `@mención` y sigue un
  salto de línea, la ventana de sugerencias de X puede "comerse" ese Enter para
  elegir la sugerencia. Revisá el texto y agregá el salto a mano si falta.
- Autocorrección o autocompletado del sitio.
- Límite de caracteres del campo (el texto se corta al llegar al máximo).

En cualquier caso, **revisá antes de publicar**.

### El cartel amarillo de "depuración" (es normal)

Mientras tipea, Chrome muestra arriba un aviso: *"Chrome está siendo controlado
por un software de depuración automática"*. **Es esperado y desaparece solo**
cuando termina el tipeo. Es el precio de que los eventos de teclado sean
reales (de los de verdad, no simulados).

Dos cosas a saber:

- **No hace falta hacer click en "Cancelar"** de ese cartel: dejalo, se va solo.
- Si lo cancelás a mitad del tipeo, el tipeo se corta en forma limpia (no queda
  nada raro escrito).

### Configuración (opcional)

Click derecho en el ícono → **Opciones**. La página abre en inglés por defecto:
tocá **Español** (arriba a la derecha) para cambiarla — recuerda tu elección.
Todo se guarda solo (se sincroniza con tu cuenta de Chrome):

- **Velocidad base**: qué tan rápido tipea (de lento a rápido).
- **Variación humana**: hace que los tiempos entre teclas no sean siempre
  iguales (más natural).
- **Pausas extra**: descansitos un poco más largos después de espacios, puntos
  y saltos de línea.
- **Pausa de "pensar"**: de vez en cuando se queda un instante "pensando".
- **Errores de tipeo** (apagado por defecto): de vez en cuando se equivoca de
  tecla y la corrige con Backspace, como una persona.
- **Tabulaciones**: los Tab del texto se reemplazan por espacios (un Tab real
  movería el cursor al siguiente campo y arruinaría el tipeo).

#### Cambiar el atajo

Si Alt + Shift + V te choca con algo: `chrome://extensions/shortcuts` →
buscá TypeClip → hacé click en el lápiz y apretá tu combinación preferida. En
Windows con dos o más distribuciones de teclado, Alt+Shift es la combinación
del sistema para "cambiar idioma" y puede estorbar — si te pasa, elegí una
combinación con Ctrl.

### Preguntas frecuentes

**¿Mi texto viaja a algún lado? ¿Se guarda?**
No. Se lee del portapapeles, se tipea y se descarta. No se guarda, no se envía,
no hay servidor, no hay permisos para leer ningún sitio web.

**¿Puede llegar a publicar/enviar solo?**
No, nunca. TypeClip solo escribe en el campo; el botón Publicar/Enviar lo
seguís apretando vos.

**Apreté el atajo y no pasa nada.**
- ¿El cursor está parpadeando en el campo de texto? Hacé click en el campo y
  probá de nuevo.
- ¿La ventana de Chrome es la que está activa? Si estás con otra aplicación
  enfocada, TypeClip se rehúsa (aviso `ERR`).
- ¿Instalaste bien la carpeta y no la moviste? Revisá el paso 5 de la
  instalación.
- ¿Configuraste otro atajo? Verificá en `chrome://extensions/shortcuts`.

**¿Funciona en Gmail / X / formularios?**
Sí, en cualquier campo de texto editable de una página web. Para sitios que
usan ventanas emergentes propias (el composer de X, el Redactar de Gmail), el
resultado puede variar según lo que haga el sitio con cada tecla; fijate en el
badge final (OK/DIF).

**¿Y en el celular?**
No: las extensiones de Chrome no existen en Android/iOS.

---

Para detalles técnicos (arquitectura, métodos de tipeo, reglas de privacidad y
la suite de pruebas automatizada), ver [DEVELOPMENT.md](DEVELOPMENT.md).
