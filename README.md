# TypeClip

Extensión de Chrome que **tipea por vos** el texto que copiaste.

La copiás normal (Ctrl+C), hacé click en el campo donde la querés (el cuadro de
texto de X/Twitter, un formulario, un mail…) y TypeClip la escribe **letra por
letra, con tiempos humanos**, como si la escribiras con el teclado. El sitio web
ve tipeo de verdad: no hay "pegado" que bloquear ni detectar.

---

## Instalación

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
6. Listo: el ícono de TypeClip (un cursor de texto verde) aparece en la barra de
   extensiones. Conviene **fijarlo** (click en la piezita de rompecabezas 🧩 y
   en la chincheta 📌 del ícono de TypeClip) para tenerlo a mano.

> Importante: no borres ni muevas la carpeta después de instalarla — Chrome la
> necesita para que la extensión siga funcionando.

## Cómo se usa

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

### Cancelar a mitad

- Apretá **Esc**, o
- volvé a ejecutar el atajo (Alt + Shift + V).

Se corta en el acto y queda lo que ya se tipeó (sin borrar nada).

## Qué significan las letras del ícono

| Letra | Color | Significado |
|---|---|---|
| `37%` | azul | Está tipeando. |
| **OK** | verde | Terminó y el texto del campo **coincide** con lo copiado. |
| **DIF** | naranja | Terminó, pero el campo **no quedó exacto** (ver abajo). |
| **ERR** | rojo | No arrancó o se cortó. Pasá el mouse por el ícono para ver el motivo. |

Para ver el detalle de OK/DIF/ERR, dejá el mouse un segundo sobre el ícono.

### ¿Por qué puede salir DIF?

El texto quedó distinto a lo copiado, casi siempre por algo que hizo **la propia
página**, no por la extensión:

- **Menciones de X/Twitter**: si una línea termina en una `@mención` y sigue un
  salto de línea, la ventana de sugerencias de X puede "comerse" ese Enter para
  elegir la sugerencia. Revisá el texto y agregá el salto a mano si falta.
- Autocorrección o autocompletado del sitio.
- Límite de caracteres del campo (el texto se corta al llegar al máximo).

En cualquier caso, **revisá antes de publicar**.

## El cartel amarillo de "depuración" (es normal)

Mientras tipea, Chrome muestra arriba un aviso: *"Chrome está siendo controlado
por un software de depuración automática"*. **Es esperado y desaparece solo**
cuando termina el tipeo. Es el precio de que los eventos de teclado sean
reales (de los de verdad, no simulados).

Dos cosas a saber:

- **No hace falta hacer click en "Cancelar"** de ese cartel: dejalo, se va solo.
- Si lo cancelás a mitad del tipeo, el tipeo se corta en forma limpia (no queda
  nada raro escrito).

## Configuración (opcional)

Click derecho en el ícono → **Opciones**. Todo se guarda solo (se sincroniza con
tu cuenta de Chrome):

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

### Cambiar el atajo

Si Alt + Shift + V te choca con algo: `chrome://extensions/shortcuts` →
buscá TypeClip → hacé click en el lápiz y apretá tu combinación preferida.

## Preguntas frecuentes

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
