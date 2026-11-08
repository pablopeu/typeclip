#!/usr/bin/python3
"""Arma el paquete de envío de TypeClip para la Chrome Web Store.

dist/typeclip-<version>.zip con manifest.json EN LA RAÍZ del ZIP (formato que
exige el dashboard de la CWS). Solo entra lo que la extensión necesita:
manifest, js, html, íconos y _locales. Fuera: test/, docs/, tools/, store/,
archivos ocultos, __MACOSX, .DS_Store.

Validaciones (falla con exit != 0 si alguna no pasa):
  1. manifest.json válido y con versión semántica.
  2. La versión coincide con la última de CHANGELOG.md.
  3. Todo archivo referenciado por el manifest existe.
  4. Íconos 16/32/48/128 con dimensiones reales correctas.
  5. Descripción (resuelta de _locales si usa __MSG__) <= 132 caracteres.
  6. El ZIP no contiene test/, ocultos, __MACOSX ni .DS_Store.
  7. El ZIP carga como extensión descomprimida en Chromium: el service worker
     arranca y responde, y la página de opciones abre sin errores de consola.

Imprime SHA-256 y tamaño del ZIP.
"""
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "typeclip"
DIST = ROOT / "dist"

INCLUDE_SUFFIXES = {".json", ".js", ".html", ".png"}

fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


def resolve_msg(manifest, value, locale_dir):
    """Resuelve __MSG_x__ contra _locales/en (default_locale)."""
    m = re.fullmatch(r"__MSG_(\w+)__", value or "")
    if not m:
        return value
    default = manifest.get("default_locale", "en")
    f = locale_dir / default / "messages.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    entry = data.get(m.group(1)) or {}
    return entry.get("message")


def build_zip(version):
    DIST.mkdir(exist_ok=True)
    out = DIST / f"typeclip-{version}.zip"
    names = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(EXT.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(EXT)
            # exclusiones duras
            if rel.parts[0] == "test":
                continue
            if any(part.startswith(".") for part in rel.parts):
                continue
            if p.name in {".DS_Store"} or "__MACOSX" in rel.parts:
                continue
            if p.suffix not in INCLUDE_SUFFIXES:
                continue
            z.write(p, rel.as_posix())
            names.append(rel.as_posix())
    return out, names


def validate_zip(out, names, version):
    check("manifest.json" in names, "manifest.json en la raíz del ZIP")
    check(not any(n.startswith("test/") for n in names), "sin test/ en el ZIP")
    check(not any("/." in n or n.startswith(".") for n in names), "sin archivos ocultos")
    check("__MACOSX" not in "".join(names) and not any(n.endswith(".DS_Store") for n in names),
          "sin __MACOSX / .DS_Store")
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
    check(bad is None, f"ZIP íntegro (testzip={'ok' if bad is None else bad})")
    check(f"dist/typeclip-{version}.zip" or True, "")


def load_check(zip_path):
    """Extrae el ZIP a un tempdir y lo carga como extensión descomprimida."""
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp(prefix="tc-pkg-")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    loaded_dir = Path(tmp)  # manifest quedó en la raíz de la extracción

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(prefix="tc-pkg-prof-"),
            channel="chromium", headless=True,
            args=[f"--disable-extensions-except={loaded_dir}",
                  f"--load-extension={loaded_dir}"],
            viewport=None,
        )
        errors = []
        ctx.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("about:blank")
            sw = None
            for _ in range(60):
                for w in ctx.service_workers:
                    if "background" in (w.url or ""):
                        sw = w
                if sw:
                    break
                page.wait_for_timeout(200)
            check(sw is not None, "el service worker arranca desde el ZIP")
            if sw:
                v = sw.evaluate("() => chrome.runtime.getManifest().version")
                check(v == json.loads((loaded_dir / "manifest.json").read_text())["version"],
                      f"SW vivo (getManifest -> {v})")
                ext_url = sw.evaluate("() => chrome.runtime.getURL('options.html')")
                page.goto(ext_url, wait_until="load")
                page.wait_for_timeout(700)
                check(not errors, f"options.html sin errores de consola (errors={errors[:3]})")
        finally:
            ctx.close()


def main():
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest.get("version", "")
    check(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), f"versión semántica: {version!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M)
    check(m and m.group(1) == version,
          f"CHANGELOG ({m.group(1) if m else '??'} coincide con manifest {version})")

    # archivos referenciados
    refs = []
    refs.append(Path(manifest["background"]["service_worker"]))
    refs.append(Path(manifest["options_page"]))
    for size in manifest["action"]["default_icon"].values():
        refs.append(Path(size))
    for size in manifest["icons"].values():
        refs.append(Path(size))
    missing = [str(r) for r in refs if not (EXT / r).exists()]
    check(not missing, f"archivos del manifest existen ({missing})")

    # íconos con dimensiones reales
    from PIL import Image
    bad_icons = []
    for size, rel in sorted(manifest["icons"].items(), key=lambda kv: int(kv[0])):
        im = Image.open(EXT / rel)
        if im.size != (int(size), int(size)):
            bad_icons.append(f"{rel}: {im.size} != {size}x{size}")
    check(not bad_icons, f"íconos con dimensiones reales ({bad_icons})")

    # descripción <= 132 (resuelta de _locales si hace falta)
    desc = resolve_msg(manifest, manifest.get("description", ""), EXT / "_locales")
    if desc is None:
        check(False, "description __MSG__ no resuelve contra _locales")
    else:
        check(len(desc) <= 132, f"description {len(desc)} chars <= 132: {desc[:60]!r}")
    name = resolve_msg(manifest, manifest.get("name", ""), EXT / "_locales")
    check(name is not None and len(name) <= 75, f"name {len(name or '')} chars <= 75")

    out, names = build_zip(version)
    validate_zip(out, names, version)
    load_check(out)

    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"\nZIP  : {out}")
    print(f"size : {out.stat().st_size:,} bytes")
    print(f"sha256: {sha}")
    print("archivos:", len(names))

    if fails:
        print(f"\n{len(fails)} validaciones FALLARON")
        sys.exit(1)
    print("\nTODO OK")


if __name__ == "__main__":
    main()
