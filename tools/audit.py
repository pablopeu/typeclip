#!/usr/bin/python3
"""Auditoría de cumplimiento para la Chrome Web Store (solo librería estándar).

Revisa el paquete de la extensión (typeclip/, sin test/) contra las reglas de
la CWS y las reglas de diseño propias de TypeClip, e imprime una tabla. Sale
con código != 0 si algo falla. No ejecuta la extensión: es análisis estático.

Uso: python3 tools/audit.py [--path typeclip]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------

# Código remoto / ofuscación / red: nada de esto puede aparecer en el paquete.
FORBIDDEN_CODE = [
    (r"\beval\s*\(", "eval()"),
    (r"\bnew\s+Function\b", "new Function"),
    (r"\bimportScripts\s*\(\s*['\"]https?:", "importScripts con URL remota"),
    (r"\bfetch\s*\(", "fetch()"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest"),
    (r"\bWebSocket\b", "WebSocket"),
    (r"\bsendBeacon\b", "sendBeacon"),
    (r"\bnavigator\.connect", "WebRTC/RTCDataChannel"),
    (r"\blocalStorage\b", "localStorage (el texto debe vivir solo en memoria)"),
    (r"\bindexedDB\b", "indexedDB"),
]
# Identificadores que transportan texto del portapapeles / del campo: jamás
# pueden estar dentro de un dbglog(...) o console.*( ... ).
SENSITIVE_VARS = [
    "clipboardText", "clip.text", "clip?.text", "textToType", "finalRead.text",
    "baseline", "expected", "plan.join", "msg.plan",
]
# Sufijos que cuentan como "uso seguro" (conteos, no contenido).
SAFE_SUFFIXES = (".length", ".status", ".codePointAt", "in s")

# Permisos → evidencia mínima de uso real en el código.
PERMISSION_EVIDENCE = {
    "debugger": [(r"chrome\.debugger\.", "chrome.debugger (CDP)")],
    "clipboardRead": [
        (r"navigator\.clipboard\.readText", "Async Clipboard API"),
        (r"execCommand\(\s*['\"]paste['\"]", "execCommand('paste')"),
    ],
    "offscreen": [(r"chrome\.offscreen\.", "chrome.offscreen")],
    "activeTab": [
        (r"chrome\.scripting\.executeScript", "inyección tras el gesto (executeScript)"),
        (r"chrome\.action\.onClicked|chrome\.commands\.onCommand",
         "gesto que otorga activeTab (click/atajo)"),
    ],
    "scripting": [(r"chrome\.scripting\.", "chrome.scripting")],
    "storage": [(r"chrome\.storage\.", "chrome.storage")],
}

# APIs chrome.* usables sin permiso extra (o cubiertas por los declarados).
# "commands" es una clave del manifest, no un permiso; su API no requiere
# ningún permiso declarable.
NO_PERMISSION_APIS = {"runtime", "action", "tabs", "windows", "i18n", "commands"}

results = []


def report(name, ok, detail=""):
    results.append((name, ok, detail))


def find_pkg(path):
    p = Path(path)
    if not (p / "manifest.json").exists():
        p = ROOT / "typeclip"
    return p


def code_files(pkg):
    """Archivos de CÓDIGO que se envían a la tienda (sin test/ ni assets)."""
    files = []
    for f in sorted(pkg.rglob("*")):
        rel = f.relative_to(pkg).as_posix()
        if not f.is_file():
            continue
        if rel.startswith("test/") or rel.startswith("icons/"):
            continue
        if f.suffix in (".js", ".html", ".json"):
            files.append(f)
    return files


def main():
    pkg = find_pkg(sys.argv[sys.argv.index("--path") + 1] if "--path" in sys.argv else ROOT / "typeclip")
    files = code_files(pkg)
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    src = {f: f.read_text(encoding="utf-8") for f in files}

    def lines_matching(pattern, exclude_html=False, skip_comments=False):
        out = []
        for f, text in src.items():
            if exclude_html and f.suffix == ".html":
                continue
            for i, ln in enumerate(text.splitlines(), 1):
                if skip_comments and ln.lstrip().startswith("//"):
                    continue
                if re.search(pattern, ln):
                    out.append((f.relative_to(pkg).as_posix(), i, ln.strip()[:100]))
        return out

    # ------------------------------------------------------------------
    print(f"\nTypeClip — auditoría CWS sobre {pkg.resolve()}\n" + "=" * 72)

    # 1) Código remoto / ofuscación / red --------------------------------
    bad = []
    for pattern, label in FORBIDDEN_CODE:
        for rel, i, ln in lines_matching(pattern):
            bad.append(f"{label}: {rel}:{i} {ln}")
    # <script src="http..."> o recursos remotos en el HTML (los <a href> a
    # sitios estáticos están permitidos: ver abajo).
    for f, text in src.items():
        if f.suffix != ".html":
            continue
        for m in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", text):
            if m.group(1).startswith(("http://", "https://", "//")):
                bad.append(f"script remoto: {f.name}: {m.group(1)}")
        for m in re.finditer(r"<(?:img|link)[^>]+src=[\"']([^\"']+)[\"']", text):
            if m.group(1).startswith(("http://", "https://", "//")):
                bad.append(f"recurso remoto: {f.name}: {m.group(1)}")
    # Minificación u ofuscación: líneas kilométricas o sin saltos.
    for f, text in src.items():
        if f.suffix == ".js":
            for i, ln in enumerate(text.splitlines(), 1):
                if len(ln) > 500:
                    bad.append(f"línea sospechosa de minificación ({len(ln)} chars): {f.name}:{i}")
    report("1. Sin código remoto, ofuscación ni red", not bad,
           "; ".join(bad[:4]) + (" …" if len(bad) > 4 else ""))

    # URLs http(s): solo <a href> estáticos con target=_blank y rel noopener.
    url_bad = []
    for f, text in src.items():
        if f.suffix != ".html":
            continue
        for m in re.finditer(r"<a\s[^>]*href=[\"'](https?://[^\"']+)[\"'][^>]*>", text):
            tag = m.group(0)
            if 'target="_blank"' not in tag or "noopener" not in tag:
                url_bad.append(f"{f.name}: {m.group(1)} (sin target=_blank/noopener)")
        # Cualquier otra URL http(s) en atributos que no sean <a href>
        for m in re.finditer(r"(?:src|href)=['\"](https?://[^'\"]+)['\"]", text):
            tag_start = text.rfind("<", 0, m.start())
            tag = text[tag_start:m.start()]
            if not tag.startswith("<a "):
                url_bad.append(f"{f.name}: {m.group(1)} (no es un <a> estático)")
    report("1b. URLs http(s) solo como enlaces estáticos", not url_bad, "; ".join(url_bad[:4]))

    # 2) CSP MV3: sin handlers inline ni <script> inline -------------------
    csp_bad = []
    for f, text in src.items():
        if f.suffix != ".html":
            continue
        for m in re.finditer(r"\son[a-z]+\s*=\s*['\"{]", text):
            csp_bad.append(f"handler inline: {f.name}: …{text[max(0, m.start()-40):m.end()+40].strip()[:90]}")
        for m in re.finditer(r"<script(?![^>]*src=)[^>]*>", text):
            csp_bad.append(f"<script> inline (sin src): {f.name}")
    report("2. CSP: sin handlers ni <script> inline", not csp_bad, "; ".join(csp_bad[:4]))

    # 3) Permisos: uso real de cada uno declarado --------------------------
    perms = manifest.get("permissions", [])
    perm_rows = []
    perm_fail = []
    for perm in perms:
        rules = PERMISSION_EVIDENCE.get(perm)
        if not rules:
            perm_fail.append(f"{perm}: sin regla de evidencia en el audit")
            continue
        found = []
        for pattern, label in rules:
            hits = lines_matching(pattern, exclude_html=True, skip_comments=True)
            if hits:
                found.append((label, hits[0][0], hits[0][1]))
        if found:
            perm_rows.append((perm, found))
        else:
            perm_fail.append(f"{perm}: declarado sin uso detectable en el código")
    report("3a. Cada permiso declarado tiene uso real", not perm_fail, "; ".join(perm_fail))
    if "host_permissions" in manifest:
        report("3b. Sin host_permissions", False, f"host_permissions presente: {manifest['host_permissions']}")
    else:
        report("3b. Sin host_permissions", True)

    # 3c) APIs chrome.* usadas vs declaradas -------------------------------
    used = set()
    for f, text in src.items():
        if f.suffix == ".js":
            used |= set(re.findall(r"chrome\.([a-zA-Z]+)\.", text))
    undeclared = sorted(
        a for a in used
        if a not in NO_PERMISSION_APIS and a not in perms
        and not any(a in rule for rule in [r[0] for r in PERMISSION_EVIDENCE.values()] for _ in [0])
    )
    # APIs que requieren "tabs": url/title/favIconUrl — solo válidas con
    # activeTab otorgado (gesto). Verificar que el flujo arranca en un gesto.
    gesture_ok = bool(lines_matching(r"chrome\.action\.onClicked|chrome\.commands\.onCommand"))
    url_reads = lines_matching(r"\bt(?:ab)?\.url\b|\bt\.url\b")
    report("3c. APIs chrome.* usadas sin permiso extra", not undeclared and gesture_ok,
           f"sin declarar: {undeclared or '—'} · gesto activeTab presente: {gesture_ok}"
           + (f" · lecturas de tab.url (cubierto por activeTab tras el gesto): {len(url_reads)}" if url_reads else ""))

    # 4) El texto del portapapeles nunca se loguea/guarda/envía -----------
    leak_bad = []
    for f, text in src.items():
        if f.suffix == ".js":
            for i, ln in enumerate(text.splitlines(), 1):
                if not re.search(r"dbglog\s*\(|console\.(log|info|warn|error|debug)", ln):
                    continue
                for v in SENSITIVE_VARS:
                    if v in ln and not any(s in ln for s in SAFE_SUFFIXES):
                        leak_bad.append(f"{f.name}:{i}: {ln.strip()[:90]}")
    # Escrituras a storage fuera de opciones (settings/uiLang).
    store_bad = []
    for f, text in src.items():
        if f.suffix == ".js" and f.name not in ("options.js",):
            for i, ln in enumerate(text.splitlines(), 1):
                if re.search(r"chrome\.storage\.(local|sync|session)\.set", ln):
                    store_bad.append(f"{f.name}:{i}: {ln.strip()[:80]}")
    report("4. Texto del portapapeles ni logueado ni guardado",
           not leak_bad and not store_bad,
           "; ".join(leak_bad[:3] + store_bad[:3]))

    # 5) test/ no es requerido por el paquete ------------------------------
    test_refs = lines_matching(r"['\"][^'\"]*test/", exclude_html=True)
    test_refs = [t for t in test_refs if "test/" in t[2]]
    report("5. Carpeta test/ sin referencias desde producción", not test_refs,
           "; ".join(f"{r}:{i}" for r, i, _ in test_refs[:4]))

    # ------------------------------------------------------------------
    # Tabla final
    # ------------------------------------------------------------------
    print(f"\n{'CHEQUEO':55} RESULTADO")
    print("-" * 72)
    fails = 0
    for name, ok, detail in results:
        print(f"{name:55} {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails += 1
            for line in (detail or "").split("; "):
                if line:
                    print(f"    · {line}")

    if perm_rows:
        print("\nEvidencia de uso de permisos:")
        for perm, found in perm_rows:
            for label, fname, lineno in found:
                print(f"    {perm:14} → {label}: {fname}:{lineno}")

    print("-" * 72)
    print(f"{'TODO OK' if fails == 0 else str(fails) + ' FALLO(S)'}\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
