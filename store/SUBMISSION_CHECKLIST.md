# TypeClip — Checklist de envío a la Chrome Web Store

Guía paso a paso **para el dueño del proyecto** (Pablo). Nada de esto lo puede
ni debe hacer un agente: requiere tu cuenta de Google, tu pago y tu decisión.
Todo lo marcado **[PEGAR]** tiene el texto exacto en `store/listing/en.md` o
`store/listing/es.md`.

Estado del paquete: `dist/typeclip-1.3.0.zip` generado y validado con
`tools/package.py` (todos los chequeos en TODO OK; SHA-256, tamaño y
lista de archivos al final).

---

## Decisiones pendientes ANTES de entrar al dashboard

1. **Licencia del repositorio** — hoy no hay archivo LICENSE. No la elige nadie
   por vos. Si querés una antes de publicar, agregala al repo (MIT/Apache-2.0/
   la que sea) — el listing no menciona licencia, así que no bloquea el envío,
   pero conviene decidir.
2. **GitHub Pages** — la política de privacidad y la demo viven en
   `docs/privacy.html` y `docs/demo.html`. Para que las URLs
   `https://pablopeu.github.io/typeclip/privacy.html` y `…/demo.html` funcionen:
   repo → Settings → Pages → Source: **Deploy from a branch** → rama `main`,
   carpeta **/docs** → Save. **Ojo**: solo funciona después de mergear a `main`
   la rama `store-readiness`. Si no querés activarlo, usá las URLs de fallback
   (raw de PRIVACY.md y el demo local) en los pasos 4 y 6.
3. **Categorías de datos del tab de privacidad** — propuesta en
   `store/listing/en.md` § "Data use disclosures". Revisión recomendada:
   declarar **User-generated content** (y evaluar sumar **Website content**,
   la opción conservadora).

---

## Pasos en el dashboard (https://chrome.google.com/webstore/devconsole)

### 1) Cuenta de desarrollador

1. Entrar con la cuenta de Google de tu propiedad (la que va a ser el "developer").
2. Pagar el registro único de desarrollador. **Monto a confirmar en el
   dashboard** (históricamente USD 5; verificar el número que te muestre).
3. Si pide verificar la cuenta / 2FA, completarlo. **Requisito exacto a
   confirmar en el dashboard** (las páginas públicas no lo detallan).

### 2) Nuevo ítem

1. "Nuevo ítem" → subir `dist/typeclip-1.3.0.zip`.
2. Debe pasar el parseo del manifest (si falla, correr
   `python3 tools/package.py` de nuevo y leer las validaciones).

### 3) Descripción del listado (inglés, idioma por defecto)

1. **Nombre**: `TypeClip` **[PEGAR]**
2. **Resumen** (≤132): el "Summary" de `store/listing/en.md` **[PEGAR]**
3. **Descripción larga**: la sección "Long description" **[PEGAR]**
4. **Categoría**: Productivity.
5. **Idioma por defecto**: English.

### 4) Gráficos

1. **Icono de tienda**: `store/assets/store-icon-128.png` (128×128 con el arte
   en 96×96; es el formato que pide la spec oficial).
2. **Screenshots** (mínimo 1, recomendadas las 5, en orden):
   `shot-1-typing.png`, `shot-2-ok.png`, `shot-3-options-en.png`,
   `shot-4-options-es.png`, `shot-5-banner.png`.
   **Antes de subirlas: revisarlas visualmente** (ver abajo).
3. **Small tile**: `small-tile-440x280.png`.
4. **Marquee** (opcional pero recomendado): `marquee-1400x560.png`.

### 5) Listado en español (idioma adicional)

1. "Add language" → Español (o español (Latinoamérica) — el que prefieras como
   alcance).
2. Nombre y textos **[PEGAR]** de `store/listing/es.md`.

### 6) Privacidad

1. **Single purpose**: texto de `store/listing/es.md`/"Single purpose" de
   `en.md` **[PEGAR]**.
2. **Justificación de permisos**: el dashboard muestra un campo por permiso —
   copiar cada fila de la tabla "Justification of each permission" de
   `store/listing/en.md` **[PEGAR]** (está en inglés; el dashboard de permisos
   suele pedir el texto en el idioma por defecto).
3. **Código remoto**: No.
4. **Uso de datos** (data use disclosures): seguir la propuesta de
   `store/listing/en.md` § "Data use disclosures" — declarar *User-generated
   content*, venta de datos **No**, uso no relacionado **No**, creditworthiness
   **No**. (Decisión final tuya; ver "Decisiones pendientes".)
5. **URL de política de privacidad**:
   `https://pablopeu.github.io/typeclip/privacy.html` (si activaste Pages) o
   `https://github.com/pablopeu/typeclip/blob/main/PRIVACY.md`.
6. **URL de soporte**: `https://github.com/pablopeu/typeclip/issues`.
7. **Homepage**: `https://github.com/pablopeu/typeclip`.

### 7) Distribución

1. Visibilidad: **Pública**.
2. Regiones: todas (default).
3. Sin "unlisted" ni "trusted testers" salvo que quieras una prueba privada
   primero (opción legítima: publicar como unlisted, probar en tu Chrome real,
   y después pasar a pública).

### 8) Instrucciones para el revisor

1. Pegar la sección "Instructions for the reviewer" de `store/listing/en.md`
   en el campo de notas al revisor (si el campo aparece en tu versión del
   dashboard) **[PEGAR]**.
2. Asegurarse de que la URL de la demo del paso 2 funcione ANTES de enviar
   (abrir en una ventana privada): `https://pablopeu.github.io/typeclip/demo.html`.

### 9) Enviar

1. "Enviar para revisión". Con el permiso `debugger` esperá una revisión manual
   (días, no horas; puede haber ronda de preguntas — ver `store/POLICY_REVIEW.md`).
2. Publicación: preferir **"deferred publish"** la primera vez (controlás el
   momento exacto de salir) — o inmediata si preferís.
3. Si llega un rechazo: leer el motivo, comparar contra `POLICY_REVIEW.md`
   (riesgos residuales ya identificados) y responder/ajustar.

### 10) Post-aprobación

1. Anotar la URL del ítem (`https://chromewebstore.google.com/detail/…`).
2. Agregar el botón/link de la CWS al README (sección Installation de ambos
   idiomas) y commitear. Recién ahí el link es real — antes no (por eso el
   README actual no lo tiene).
3. Merge de `store-readiness` a `main` + tag `v1.3.0` + release con el ZIP.

---

## Verificación manual previa al envío (hacerla vos, en tu Chrome real)

Nada de esto lo puede validar el arnés headless de la máquina — es la
verificación de que la extensión anda como la va a usar gente real:

1. **Atajo real**: en una pestaña `http(s)` cualquiera (p.ej. la demo), copiar
   texto, hacer click en el campo y apretar **Alt+Shift+V** de verdad (el arnés
   invoca `invoke()` porque headless no dispara comandos; acá se prueba el
   camino completo: teclado → comando → activeTab).
2. **Click en el ícono** de la barra de extensiones (el otro camino de
   invocación): mismo resultado esperado — tipea con cartel amarillo visible y
   badge de progreso.
3. **Composer real** de tu preferencia (el que uses a diario): texto corto,
   verificar que tipea y que **no aprieta Publicar/Enviar solo**.
4. **Esc a mitad**: corta en el acto, el cartel amarillo desaparece solo.
5. **Revisión visual de los screenshots** (`store/assets/shot-*.png`): que se
   lean bien, que los textos overlay no pisen nada importante, que el gráfico
   del banner (shot 5) se entienda como diagrama y no como captura falsa.
   Regenerar con `python3 tools/store_assets.py` si hay que ajustar algo.

## Regenerar todo (si cambiás algo)

```bash
python3 tools/audit.py          # auditoría estática — tiene que dar TODO OK
python3 tools/e2e.py            # suite E2E — tiene que dar 37/37
python3 tools/store_assets.py   # regenera screenshots/tiles/icono
python3 tools/package.py        # regenera el ZIP + SHA-256
```

## Datos del paquete

- ZIP: `dist/typeclip-1.3.0.zip` (13 archivos, manifest en la raíz)
- SHA-256: `ca1f5c646bf7b6dc0aeebff2d212b1b60287d68fe24bc27edd27d8a6b045fc51`
- Tamaño: 43.013 bytes
- Generado: 2026-11-08 (rama `store-readiness`, sin push ni tag)
