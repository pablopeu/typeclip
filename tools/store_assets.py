#!/usr/bin/python3
"""Genera los assets de la Chrome Web Store para TypeClip.

Salidas en store/assets/:
  - shot-1-typing.png    1280x800  demo page, tipeo real cancelado a mitad
  - shot-2-ok.png        1280x800  demo page, campo completo tras el tipeo
  - shot-3-options-en.png 1280x800 página de opciones (inglés)
  - shot-4-options-es.png 1280x800 página de opciones (español)
  - shot-5-banner.png    1280x800  gráfico explicativo del cartel amarillo
  - store-icon-128.png   128x128   RGBA: arte 96x96 + margen transparente
                                  (spec oficial del icono de tienda)
  - small-tile-440x280.png  440x280  RGB sin alfa
  - marquee-1400x560.png   1400x560  RGB sin alfa

Notas de honestidad: las capturas 1 y 2 muestran la página de demo REAL con
texto tipeado de verdad por la extensión (la 1 quedó a mitad porque se canceló
el tipeo con la re-invocación — exactamente el estado que vería un usuario).
La 5 es un gráfico ESQUEMÁTICO del cartel de Chrome (en headless no existe la
UI del browser), dibujado como diagrama y no como falsa captura.
"""
import shutil
import sys
import time
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "typeclip"
DOCS = ROOT / "docs"
OUT = ROOT / "store" / "assets"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

DEMO_TEXT = (
    "Hi! This text came from the clipboard and it is being typed key by key, "
    "with human timing, right into this field. No paste involved."
)

TITLES = {
    "shot-1-typing.png": "It types your clipboard, key by key",
    "shot-2-ok.png": "Done — verified against the clipboard",
    "shot-3-options-en.png": "Speed, pauses, mistakes — your call",
    "shot-4-options-es.png": "Opciones en español (y en inglés)",
}


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def wait_badge(sw, want, timeout_s=90):
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            b = sw.evaluate("() => chrome.tabs.query({active:true,lastFocusedWindow:true})"
                            ".then(([t]) => t ? chrome.action.getBadgeText({tabId:t.id}) : null)")
        except Exception:
            b = None
        if b == want:
            return True
        time.sleep(0.4)
    return False


def find_sw(ctx, page):
    for _ in range(60):
        for w in ctx.service_workers:
            if "background" in (w.url or ""):
                return w
        page.wait_for_timeout(200)
    return None


def overlay_title(src, dst, title):
    """Banda inferior semitransparente con título corto (estilo captura CWS)."""
    im = Image.open(src).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    f = font(30)
    tw = d.textlength(title, font=f)
    pad_x, band_h = 22, 66
    x0, y0 = 24, H - band_h - 24
    d.rounded_rectangle([x0, y0, x0 + tw + pad_x * 2, y0 + band_h], radius=14,
                        fill=(20, 22, 26, 205))
    d.text((x0 + pad_x, y0 + (band_h - 30) / 2 - 2), title, font=f, fill=(255, 255, 255, 255))
    im.convert("RGB").save(dst, "PNG")  # RGB 24-bit, sin alfa
    print("ok  ", dst.name, im.size)


def wrap_lines(d, text, f, max_w):
    """Corta `text` en líneas que entren en `max_w` píxeles."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        if d.textlength(probe, font=f) <= max_w or not cur:
            cur = probe
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def banner_graphic(dst):
    """Gráfico esquemático del infobar amarillo: fondo y layout propios, NO es
    una captura de browser (en headless no existe la UI del browser)."""
    W, H = 1280, 800
    im = Image.new("RGB", (W, H), (247, 248, 250))
    d = ImageDraw.Draw(im)
    # franja superior estilo "browser" (esquema, no captura)
    top_h = 92
    d.rectangle([0, 0, W, top_h], fill=(241, 243, 244))
    d.line([0, top_h, W, top_h], fill=(160, 165, 170), width=2)
    for i, c in enumerate([(218, 86, 78), (232, 178, 63), (98, 190, 96)]):
        d.ellipse([30 + i * 34, top_h / 2 - 8, 46 + i * 34, top_h / 2 + 8], fill=c)
    f20 = font(20)
    d.rounded_rectangle([W - 340, 24, W - 30, top_h - 24], radius=20,
                        fill=(255, 255, 255), outline=(160, 165, 170), width=2)
    d.text((W - 185 - d.textlength("typeclip demo", font=f20) / 2, 34),
           "typeclip demo", font=f20, fill=(90, 94, 100))
    # banner amarillo
    by = top_h + 14
    d.rounded_rectangle([40, by, W - 40, by + 64], radius=10, fill=(253, 234, 156),
                        outline=(190, 160, 40), width=2)
    d.text((60, by + 18), "Chrome is being controlled by automated test software",
           font=font(24), fill=(60, 50, 10))
    # tarjeta blanca con la explicación (el texto no pisa contenido de página)
    cx0, cy0, cx1, cy1 = 40, by + 86, W - 40, H - 40
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=18, fill=(255, 255, 255),
                        outline=(226, 229, 234), width=2)
    px = cx0 + 50
    max_w = cx1 - px - 50
    title = "That yellow banner is normal"
    d.text((px, cy0 + 40), title, font=font(40), fill=(31, 35, 40))
    body = ("While TypeClip types, Chrome shows this banner: it means real keyboard "
            "events are being sent to the page. It disappears by itself the moment "
            "typing ends — or when you cancel with Esc.")
    f28 = font(28, bold=False)
    y = cy0 + 118
    for ln in wrap_lines(d, body, f28, max_w):
        d.text((px, y), ln, font=f28, fill=(55, 61, 68))
        y += 42
    note = "— explanatory diagram, not a real browser screenshot —"
    d.text((px, cy1 - 56), note, font=font(22, bold=False), fill=(120, 126, 134))
    im.save(dst, "PNG")
    print("ok  ", dst.name, im.size)


def make_store_icon(dst):
    """Spec oficial CWS: canvas 128x128 TRANSPARENTE con el arte en 96x96
    (16 px de margen por lado; la tienda le pone el marco redondeado).
    Divergencia consciente del brief ('sin alfa'): el icono de tienda es el
    único asset donde la spec oficial pide transparencia."""
    art = Image.open(EXT / "icons" / "icon128.png").convert("RGBA")
    art96 = art.resize((96, 96), Image.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    canvas.paste(art96, (16, 16), art96)
    canvas.save(dst, "PNG")
    print("ok  ", dst.name, canvas.size)


def tile(dst, w, h, tagline, logo_px, name_px, tag_px):
    """Tile promocional (440x280 y 1400x560), RGB sin alfa."""
    bg = (247, 243, 236)          # papel cálido
    ink = (32, 34, 38)
    accent = (232, 122, 34)       # la C naranja del logo
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    logo = Image.open(ROOT / "TC.png").convert("RGBA")
    logo = logo.resize((logo_px, int(logo_px * logo.height / logo.width)), Image.LANCZOS)
    lx, ly = int(w * 0.08), int((h - logo.height) / 2)
    im.paste(logo, (lx, ly), logo)
    tx = lx + logo.width + int(w * 0.05)
    name = "TypeClip"
    nf = font(name_px)
    d.text((tx, int(h * 0.26)), name, font=nf, fill=ink)
    d.text((tx + d.textlength(name, font=nf) + name_px * 0.35, int(h * 0.26) + name_px * 0.72),
           "TC", font=font(int(name_px * 0.45)), fill=accent)
    tf = font(tag_px, bold=False)
    # tagline en hasta 2 líneas
    lines = tagline.split("\n")
    for i, ln in enumerate(lines):
        d.text((tx, int(h * 0.52) + i * int(tag_px * 1.45)), ln, font=tf, fill=(90, 94, 100))
    d.rounded_rectangle([tx, int(h * 0.80), tx + int(w * 0.42), int(h * 0.80) + int(h * 0.10)],
                        radius=int(h * 0.05), outline=accent, width=max(2, h // 200))
    sf = font(int(tag_px * 0.8))
    d.text((tx + int(w * 0.03), int(h * 0.80) + int(h * 0.025)),
           "free · source on GitHub", font=sf, fill=accent)
    im.save(dst, "PNG")
    print("ok  ", dst.name, im.size)


def verify(assets):
    """Chequeo mecánico: dimensiones exactas y modo (RGB sin alfa salvo el icono)."""
    specs = {
        "shot-1-typing.png": ((1280, 800), "RGB"),
        "shot-2-ok.png": ((1280, 800), "RGB"),
        "shot-3-options-en.png": ((1280, 800), "RGB"),
        "shot-4-options-es.png": ((1280, 800), "RGB"),
        "shot-5-banner.png": ((1280, 800), "RGB"),
        "store-icon-128.png": ((128, 128), "RGBA"),
        "small-tile-440x280.png": ((440, 280), "RGB"),
        "marquee-1400x560.png": ((1400, 560), "RGB"),
    }
    fails = 0
    for name, (size, mode) in specs.items():
        p = OUT / name
        if not p.exists():
            print("FAIL", name, "no existe"); fails += 1; continue
        im = Image.open(p)
        ok = im.size == size and im.mode == mode
        if mode == "RGB" and "A" in im.getbands():
            ok = False
        print("ok  " if ok else "FAIL", f"{name}: {im.size} {im.mode} (esperado {size} {mode})")
        fails += 0 if ok else 1
    return fails


def prepare_ext_copy():
    """Copia la extensión a un tempdir y le agrega docs/demo.html.

    La demo tiene que correr desde el ORIGEN DE LA EXTENSIÓN: sin un gesto de
    usuario real no se otorga activeTab y la extensión no puede inyectar
    content.js en una página http (este script invoca `invoke()` directo desde
    el SW, sin click). El page.screenshot no captura la barra de direcciones,
    así que el resultado es idéntico a la demo publicada en GitHub Pages.
    """
    tmp = Path(tempfile.mkdtemp(prefix="tc-assets-ext-"))
    dst = tmp / "typeclip"
    shutil.copytree(EXT, dst)
    shutil.copy(DOCS / "demo.html", dst / "demo.html")
    # chrome.scripting no puede inyectar en páginas chrome-extension:// (ni en
    # las propias): sube la 404 del <script src="content.js">. La copia lo carga
    # como la página de test; background.js lo sondea por mensaje (init).
    demo = dst / "demo.html"
    demo.write_text(demo.read_text(encoding="utf-8").replace(
        "</body>", '<script src="content.js"></script>\n</body>'), encoding="utf-8")
    return tmp, dst


def write_clipboard(page, text):
    """Deja `text` en el portapapeles del sistema.

    Un origen chrome-extension:// es "opaque" para Browser.grantPermissions y
    la Async Clipboard API sin permiso se rechaza (probado: portapapeles vacío
    y tipeo ERR). El camino confiable es el mismo del arnés E2E: un CLICK real
    sobre un botón temporal cuyo handler hace selección + execCommand("copy")
    — con gesto de usuario, sin permisos.
    """
    page.evaluate("""t => {
      const old = document.getElementById('__tc_copy_btn');
      if (old) old.remove();
      window.__tcCopyOk = undefined;
      const btn = document.createElement('button');
      btn.id = '__tc_copy_btn';
      btn.textContent = 'copy';
      btn.style.cssText = 'position:fixed;left:8px;top:8px;z-index:2147483647';
      btn.addEventListener('click', async () => {
        // Con activación transitoria (el click real) writeText se permite sin
        // permiso. Si igual falla, execCommand("copy") como red de seguridad.
        let ok = false;
        try { await navigator.clipboard.writeText(t); ok = true; } catch (e) { ok = false; }
        if (!ok) {
          const ta = document.createElement('textarea');
          ta.id = '__tc_clip_tmp';
          ta.value = t;
          ta.style.cssText = 'position:fixed;left:8px;top:8px;width:10px;height:10px;opacity:.01';
          document.body.appendChild(ta);
          ta.focus(); ta.select();
          ok = document.execCommand('copy');
          ta.remove();
        }
        window.__tcCopyOk = ok;
        btn.remove();
      });
      document.body.appendChild(btn);
    }""", text)
    page.click("#__tc_copy_btn")
    for _ in range(50):
        if page.evaluate("() => window.__tcCopyOk !== undefined"):
            break
        time.sleep(0.1)
    if not page.evaluate("() => !!window.__tcCopyOk"):
        raise RuntimeError("no se pudo copiar el texto al portapapeles")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp_ext, ext_run = prepare_ext_copy()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(prefix="tc-assets-"),
            channel="chromium", headless=True,
            args=[f"--disable-extensions-except={ext_run}", f"--load-extension={ext_run}",
                  "--hide-scrollbars"],
            # Viewport explícito: con viewport=None el headless de Playwright
            # quedó en 1280x720 (--window-size no manda) y la CWS exige
            # exactamente 1280x800.
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("about:blank")
        sw = find_sw(ctx, page)
        if not sw:
            print("FAIL: no cargó el service worker"); shutil.rmtree(tmp_ext, ignore_errors=True)
            sys.exit(1)
        try:
            # El origen chrome-extension:// no admite grant_permissions (origins
            # opacos para CDP): write_clipboard copia dentro del handler de un
            # click real (activación transitoria), sin permiso.
            demo_url = sw.evaluate("() => chrome.runtime.getURL('demo.html')")
            page.goto(demo_url, wait_until="load")
            page.wait_for_timeout(400)

            # --- captura 1: tipeo real cancelado a mitad (estado real) -------
            sw.evaluate("() => chrome.storage.sync.set({settings: {wpm: 140, jitter: 25,"
                        " pauses: true, thinkPct: 0, typos: false, typoPct: 0,"
                        " tabMode: 'spaces', tabSpaces: 4}})")
            page.wait_for_timeout(300)
            write_clipboard(page, DEMO_TEXT)
            page.click("#ta")
            sw.evaluate("() => { invoke(); }")     # arranca el tipeo real
            time.sleep(2.4)                        # mitad del texto aprox
            sw.evaluate("() => { invoke(); }")     # re-invocación = cancelar
            page.wait_for_timeout(1500)            # detach → CDP destrabado
            part = page.evaluate("() => document.getElementById('ta').value")
            if not (0 < len(part) < len(DEMO_TEXT)):
                raise RuntimeError(f"captura 1 no quedó a mitad de tipeo: {part[:60]!r}")
            page.screenshot(path=str(OUT / "raw-1.png"))

            # --- captura 2: tipeo completo, badge OK --------------------------
            page.click("#ta")
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            write_clipboard(page, DEMO_TEXT)
            page.click("#ta")  # el click del copiado se llevó el foco del campo
            sw.evaluate("() => { invoke(); }")
            ok2 = wait_badge(sw, "OK", 60)
            got2 = page.evaluate("() => document.getElementById('ta').value")
            if not ok2 or got2 != DEMO_TEXT:
                raise RuntimeError(f"captura 2 sin tipeo verificado: badge_ok={ok2} got={got2[:60]!r}")
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "raw-2.png"))

            # --- capturas 3/4: opciones EN/ES --------------------------------
            ext_url = sw.evaluate("() => chrome.runtime.getURL('options.html')")
            page.goto(ext_url, wait_until="load")
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / "raw-3.png"))
            page.click("#langEs")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / "raw-4.png"))
        finally:
            ctx.close()
    shutil.rmtree(tmp_ext, ignore_errors=True)

    # --- post-proceso ---------------------------------------------------------
    for raw, name in [("raw-1.png", "shot-1-typing.png"), ("raw-2.png", "shot-2-ok.png"),
                      ("raw-3.png", "shot-3-options-en.png"), ("raw-4.png", "shot-4-options-es.png")]:
        overlay_title(OUT / raw, OUT / name, TITLES[name])
        (OUT / raw).unlink()
    banner_graphic(OUT / "shot-5-banner.png")
    make_store_icon(OUT / "store-icon-128.png")
    tile(OUT / "small-tile-440x280.png", 440, 280,
         "Your clipboard,\ntyped like a person.",
         logo_px=104, name_px=40, tag_px=17)
    tile(OUT / "marquee-1400x560.png", 1400, 560,
         "Your clipboard, typed key by key with real keyboard events.\n"
         "Nothing stored. Nothing sent. Esc cancels anytime.",
         logo_px=200, name_px=84, tag_px=30)

    fails = verify(OUT)
    print("\nTODO OK" if not fails else f"\n{fails} problemas")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
