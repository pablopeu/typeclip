# Ficha de Chrome Web Store — Español (idioma adicional)

## Nombre

TypeClip

## Resumen (descripción corta, ≤132 caracteres — campo del dashboard)

Tipea el texto que copiaste, letra por letra con eventos de teclado reales,
en el campo que elijas. No guarda ni envía nada.

*(124 caracteres — verificado.)*

## Categoría

**Productividad** (la misma que el idioma principal; el dashboard no permite
categorías por idioma).

## Propósito único (campo del dashboard, traducción fiel del inglés)

Tipea el texto del portapapeles en el campo enfocado, letra por letra, por
comando explícito del usuario.

## Descripción larga (campo del dashboard)

TypeClip tipea por vos el texto que copiaste.

Copiá como siempre (Ctrl+C), hacé click en el campo donde lo querés —el
compositor de una publicación, un formulario, un mail— y TypeClip lo escribe
caracter a caracter, con tiempos humanos, como si lo estuvieras tipeando vos.
La página recibe eventos de teclado reales, lo que además lo hace útil en
campos que bloquean o restringen el pegado.

• Eventos de teclado reales, vía el protocolo de depuración de Chrome.
Mientras tipea, Chrome muestra su cartel de "controlado por software de
pruebas automatizadas" — es esperado, desaparece solo al terminar, y el
debugger se libera en el acto.

• Ritmo humano: velocidad base, variación natural, pequeñas pausas; y si
querés, hasta comete errores de tipeo y los corrige con Backspace, como una
persona.

• Privacidad primero: el texto se lee del portapapeles solo en el momento en
que ejecutás TypeClip, vive únicamente en memoria y nunca se guarda ni se
envía a ningún lado. Sin analítica, sin terceros, sin código remoto.

• Vos mandás: nunca aprieta Publicar ni Enviar, nunca envía formularios y
nunca te cambia el foco. Esc (o volver a ejecutarlo) cancela al instante,
dejando lo que ya quedó tipeado.

• Funciona en cualquier campo editable de una página web: inputs de una línea,
textareas y editores enriquecidos contenteditable. Los sitios con editores
emergentes propios pueden comportarse distinto; mirá el badge OK / DIF del
ícono al terminar.

• Configurable: velocidad, pausas, errores, manejo de Tab — y la página de
opciones está en inglés y español.

Limitaciones: solo Chrome de escritorio (no hay versión para celulares). Si
el campo tiene longitud máxima, el texto se corta en el límite. El cartel
amarillo mientras tipea es parte de cómo funcionan los eventos de teclado
reales en Chrome.

Código fuente: github.com/pablopeu/typeclip

## ¿Usa código remoto? (campo del dashboard)

**No.** Toda la lógica viene dentro del paquete; no hay pedidos de red de
ningún tipo (verificable con `tools/audit.py` en el repositorio).

## URLs

Las mismas del idioma principal (GitHub del proyecto, issues y política de
privacidad).

## Instrucciones para el revisor

Ver la versión en inglés (`store/listing/en.md`): la página de demo es
https://pablopeu.github.io/typeclip/demo.html (o `docs/demo.html` del repo
servida por http:// si GitHub Pages todavía no está activado).

## Uso de datos (campos de privacidad del dashboard)

Ver la propuesta completa en `store/listing/en.md` (sección "Data use
disclosures"): declarar "User-generated content" (contenido generado por el
usuario) con todas las opciones de venta/uso no relacionado en **No**. La
decisión final la toma el dueño del proyecto desde el dashboard.
