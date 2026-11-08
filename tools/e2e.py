#!/usr/bin/python3
"""E2E de TypeClip contra Chromium real (headless nuevo, channel=chromium) con la
extensión cargada por --load-extension. La página de prueba se sirve en
0.0.0.0:8737 (regla de la estación). Resultados por subtest + resumen final."""
import json
import re
import sys
import threading
import functools
import http.server
import time
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "typeclip"
TESTDIR = EXT / "test"
PORT = 8737
BASE = f"http://127.0.0.1:{PORT}/index.html"

from playwright.sync_api import sync_playwright  # noqa: E402

results = []


def log(*a):
    print(*a, flush=True)


def report(name, ok, detail=""):
    results.append((name, ok, detail))
    log(f"[{'PASS' if ok else 'FAIL'}] {name} {('— ' + detail) if detail else ''}")


PAYLOADS = {
    "simple": "Hola mundo, esto es una prueba simple de TypeClip.",
    "x280": ("Prueba del composer con 280+ caracteres: ñandú, garçon, ¿cómo estás?, ¡holaaa! "
             "Café con leche ☕ y un emoji de cohete 🚀.\nSegunda línea que termina mencionando a @pablo\n"
             "Tercer línea: enough, already; testing: enter keys & symbols $100 * 3 = ?"),
}
_frases = [
    "El ñandú corrió por la pampa hasta que el sol se puso.",
    "¿Cuánto cuesta un café con leche en París? ¡Depende del barrio!",
    "Párrafo con números 12345 y símbolos raros: @user #tag $50% & (más).",
    "Línea con emoji 🚀 y otro ☕ para probar pares surrogate.",
    "A quick brown fox jumps over the lazy dog, again and again.",
]
_s = ""
_i = 0
while len(_s) < 2200:
    _s += _frases[_i % len(_frases)] + "\n"
    _i += 1
PAYLOADS["largo"] = _s


def norm(t):
    return t.replace("\r\n", "\n").replace("\r", "\n")


def field_text(page, sel):
    return page.eval_on_selector(sel, "el => el.tagName === 'DIV' ? el.innerText : el.value")


def badge(sw):
    return sw.evaluate("() => chrome.tabs.query({active:true,lastFocusedWindow:true})"
                       ".then(([t]) => t ? chrome.action.getBadgeText({tabId:t.id}) : null)")


def badge_tooltip(sw):
    return sw.evaluate("() => chrome.tabs.query({active:true,lastFocusedWindow:true})"
                       ".then(([t]) => t ? chrome.action.getTitle({tabId:t.id}) : null)")


def set_settings(sw, **s):
    base = {"wpm": 180, "jitter": 20, "pauses": True, "thinkPct": 1, "typos": False,
            "typoPct": 1.5, "tabMode": "spaces", "tabSpaces": 4}
    base.update(s)
    sw.evaluate(f"() => chrome.storage.sync.set({{settings: {json.dumps(base)}}})")
    time.sleep(0.3)


def invoke(sw):
    # En headless los comandos de extensión no se disparan con teclas CDP, así
    # que el arnés invoca la misma función que ejecuta el listener del comando.
    # FIRE-AND-FORGET: invoke() es async y resuelve al TERMINAR la sesión; si el
    # evaluate esperara la promise, el arnés quedaría bloqueado ~110 s por tipeo
    # y un segundo invoke (toggle/Esc) llegaría cuando ya no hay sesión activa.
    sw.evaluate("() => { invoke(); }")


def prep(page, sel, payload):
    """Limpia el log, carga el payload en el portapapeles y deja el foco en el campo."""
    page.click("#clear")
    page.click(f"[data-payload='{payload}']")
    page.wait_for_function("() => document.getElementById('clipStatus').textContent.startsWith('✓')", timeout=5000)
    page.click(sel)
    # Limpiar con teclas reales: fill() de Playwright dispara un evento input
    # con data='' que contaminaría el diagnóstico (y de paso prueba que el
    # propio arnés también respeta las reglas).
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")


def wait_value(page, sel, expected, timeout_ms, interval=0.3):
    exp = norm(expected)
    end = time.time() + timeout_ms / 1000
    while time.time() < end:
        if norm(field_text(page, sel)) == exp:
            return True
        # sleep de Python (NO page.wait_for_timeout): el callback del timer viaja
        # por CDP y se encola detrás de los miles de key events del tipeo, lo que
        # hacía que el loop se pase de la deadline por minutos. En textos largos
        # conviene interval alto: cada poll compite por el pipeline CDP y baja el
        # ritmo real de tipeo.
        time.sleep(interval)
    return False


def first_diff(a, b):
    """Índice y contexto de la primera diferencia entre dos strings."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    ctx_a = repr(a[max(0, i - 25):i + 25])
    ctx_b = repr(b[max(0, i - 25):i + 25])
    return f"primera dif @ {i} (len {len(a)} vs {len(b)}): campo={ctx_a} esperado={ctx_b}"


def wait_stable(page, sel, timeout_ms, stable_ms=2500):
    """Espera a que el campo deje de cambiar (tipeo terminado o cancelado)."""
    end = time.time() + timeout_ms / 1000
    last, t0 = None, time.time()
    while time.time() < end:
        cur = field_text(page, sel)
        if cur == last:
            if time.time() - t0 >= stable_ms / 1000:
                return cur
        else:
            last, t0 = cur, time.time()
        time.sleep(0.3)
    return last


def run_verify(page):
    page.click("#verify")
    return page.inner_text("#verifyOut")


def verify_detail(v):
    bad = [ln for ln in v.split("\n") if ln.startswith("✗")]
    return "; ".join(bad) if bad else v.split("\n")[0]


def dump_evidence(page, sw, tag):
    """Evidencia forense de un fallo: texto completo del campo, log de eventos
    de la página (array en memoria window.__events) y ring-buffer del SW."""
    Path(f"/tmp/e-{tag}-field.txt").write_text(field_text(page, "#ta") or "")
    evs = page.evaluate(
        "() => (window.__events || []).map(r =>"
        " [r.t, r.type, r.isTrusted, r.key, r.code, r.keyCode, r.inputType, r.data, r.extra]"
        ".join('\\t')).join('\\n')")
    Path(f"/tmp/e-{tag}-events.tsv").write_text(evs or "")
    dbg = sw.evaluate("() => globalThis.__typeclipDbg ? globalThis.__typeclipDbg() : ['sin dbg']")
    Path(f"/tmp/e-{tag}-swdbg.txt").write_text("\n".join(dbg))
    log(f"evidencia en /tmp/e-{tag}-{{field.txt,events.tsv,swdbg.txt}}")


def sw_last_outcome(sw):
    """Último 'outcome' del ring-buffer del SW: p.ej. 'done CDP session=viva'."""
    lines = sw.evaluate("() => globalThis.__typeclipDbg ? globalThis.__typeclipDbg() : []")
    for ln in reversed(lines):
        if "outcome" in ln:
            return ln.split("] ", 1)[1]
    return "sin outcome"


def main():
    import os
    only = os.environ.get("ONLY")  # p.ej. ONLY=E corre solo ese bloque de subtests

    def active(key):
        return not only or key in only.split(",")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(TESTDIR))
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    ctx = sync_playwright().start().chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-e2e-"),
        channel="chromium", headless=True,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--window-size=1400,1000"],
        viewport=None,
    )
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
        if not sw:
            report("service worker cargado", False, "no apareció")
            raise SystemExit(1)
        report("service worker cargado", True)

        # La página de prueba corre desde el ORIGEN DE LA EXTENSIÓN: los comandos
        # de extensión no se disparan con teclado sintético CDP en headless (y sin
        # invocación real activeTab no se otorga), así que el arnés llama a
        # invoke() directamente en el SW y la página carga content.js ella misma.
        # chrome.debugger.attach funciona igual → el método CDP se ejercita real.
        EXT_PAGE = sw.evaluate("() => chrome.runtime.getURL('test/index.html')")
        page.goto(EXT_PAGE, wait_until="load")
        log("página de prueba:", EXT_PAGE)
        # El payload "largo" lo define LA PÁGINA (fuente única de verdad): lo que
        # se copia al portapapeles es exactamente lo que el arnés espera.
        PAYLOADS["largo"] = page.evaluate("() => window.__payloads.largo")
        assert len(PAYLOADS["largo"]) > 2000, "payload largo demasiado corto"
        PAYLOADS["multiline"] = page.evaluate("() => window.__payloads.multiline")
        PAYLOADS["especiales"] = page.evaluate("() => window.__payloads.especiales")

        # ---------------- A) input + criterio 6 (eventos trusted) ----------------
        set_settings(sw)
        prep(page, "#inp", "simple")
        invoke(sw)
        ok = wait_value(page, "#inp", PAYLOADS["simple"], 30000)
        report("A) input de formulario — texto completo", ok,
               "" if ok else f"quedó: {field_text(page, '#inp')!r}")
        v = run_verify(page)
        report("A) criterio 6 — eventos trusted sin paste", "TODO OK" in v, verify_detail(v))
        b, tip = badge(sw), badge_tooltip(sw)
        report("A) badge OK + método CDP", b == "OK" and "CDP" in tip, f"badge={b!r} tip={tip[:70]!r}")

        # ---------------- B) textarea con 280+ caracteres especiales ------------
        prep(page, "#ta", "x280")
        invoke(sw)
        ok = wait_value(page, "#ta", PAYLOADS["x280"], 90000)
        report("B) textarea 280+ (tildes ñ ¿¡ emoji \\n @)", ok,
               "" if ok else f"quedó: {field_text(page, '#ta')[:100]!r}…")
        v = run_verify(page)
        report("B) criterio 6 — diagnósticos", "TODO OK" in v, verify_detail(v))

        # ---------------- C) contenteditable ------------------------------------
        prep(page, "#ce", "x280")
        invoke(sw)
        got = wait_stable(page, "#ce", 90000)
        ok = norm(got) == norm(PAYLOADS["x280"])
        report("C) contenteditable 280+", ok, "" if ok else f"quedó: {got[:100]!r}…")
        v = run_verify(page)
        report("C) criterio 6 — diagnósticos", "TODO OK" in v, verify_detail(v))

        # ---------------- D) composer fake tipo X (mención come Enter) ---------
        prep(page, "#xce", "x280")
        invoke(sw)
        got = wait_stable(page, "#xce", 90000)
        time.sleep(1)
        b, tip = badge(sw), badge_tooltip(sw)
        eaten = page.eval_on_selector("#xce", "el => el.dataset.mentionEaten || '0'")
        report("D) X fake: el typeahead se comió el Enter", str(eaten) != "0", f"mentionEaten={eaten}")
        report("D) X fake: badge DIF con tooltip explicativo", b == "DIF" and "NO coincide" in tip,
               f"badge={b!r} tip={tip[:80]!r}")

        # ---------------- E) 2000+ caracteres (ciclo de vida del SW) -----------
        set_settings(sw, wpm=250, jitter=10, pauses=False, thinkPct=0)
        prep(page, "#ta", "largo")
        t0 = time.time()
        invoke(sw)
        ok = wait_value(page, "#ta", PAYLOADS["largo"], 600000, interval=1.5)
        dur = time.time() - t0
        b = badge(sw)
        det = f"{len(PAYLOADS['largo'])} chars en {dur:.0f}s badge={b!r} · {sw_last_outcome(sw)}"
        if not ok:
            det += " | " + first_diff(norm(field_text(page, "#ta")), norm(PAYLOADS["largo"]))
            dump_evidence(page, sw, "e")
        report("E) 2000+ caracteres de corrido", ok and b == "OK", det)
        report("E) sin corte por ciclo de vida del SW", "done CDP" in sw_last_outcome(sw),
               sw_last_outcome(sw))

        # ---------------- F) cancelación ----------------------------------------
        # NOTA CLAVE del arnés: mientras chrome.debugger está adjunto, TODO el
        # tráfico CDP de Playwright hacia esa pestaña se encola detrás de los
        # comandos del debugger (los eval no se ejecutan hasta el detach, y un
        # page.keyboard.press("Escape") llegaría DESPUÉS del tipeo). Para probar
        # el Esc REAL se despacha un keyDown/keyUp de Escape CONFIABLE a través
        # de la PROPIA sesión de debugger de la extensión (sw.evaluate →
        # chrome.debugger.sendCommand): el comando se intercala dentro del
        # pipeline del tipeo, la página recibe el keydown trusted, el listener
        # del content script manda {tc:'esc'} con el sender correcto y el guard
        # del SW (sender.tab.id === session.tabId) lo acepta. Camino 100% real
        # desde el keydown en adelante.
        ESC_KEYS = """() => chrome.tabs.query({ active: true, lastFocusedWindow: true }).then(([t]) =>
            Promise.all([
              chrome.debugger.sendCommand({ tabId: t.id }, 'Input.dispatchKeyEvent',
                { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 }),
              chrome.debugger.sendCommand({ tabId: t.id }, 'Input.dispatchKeyEvent',
                { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 }),
            ])).catch(e => 'esc-keys (ok si canceló primero): ' + e.message)"""

        invoke(sw)  # el campo #ta sigue enfocado con contenido largo
        time.sleep(2.5)
        sw.evaluate(ESC_KEYS)
        time.sleep(1.5)
        # Al cancelar hay detach → los eval a la pestaña se destraban solos.
        mid = len(field_text(page, "#ta"))
        seq = []
        for _ in range(8):
            seq.append(badge(sw))
            time.sleep(0.5)
        after = len(field_text(page, "#ta"))
        dbg_f = sw.evaluate("() => globalThis.__typeclipDbg()")
        ok_f = mid == after and mid > 0 and all(x == "" for x in seq) and any("cancel" in x for x in dbg_f)
        det = f"mid={mid} after={after} seq={seq}"
        if not ok_f:
            det += "\nDBG SW: " + " || ".join(dbg_f[-20:])
        report("F) cancelación por Esc (keydown trusted vía debugger)", ok_f, det)
        # El Esc de cancelación debe TRAGARSE (document-captura, preventDefault +
        # stopImmediatePropagation): si llega al campo, el sitio lo procesa
        # (p.ej. X abre "guardar borrador"). El contador vive en la página.
        esc_seen = page.evaluate("() => window.__escSeen || 0")
        report("F) Esc cancela sin llegar al sitio (tragado)", esc_seen == 0, f"escSeen={esc_seen}")

        # Cancelación por re-invocación del atajo (toggle) — camino invoke().
        invoke(sw)
        time.sleep(2.0)
        invoke(sw)  # toggle → cancel
        time.sleep(1.5)
        mid2 = len(field_text(page, "#ta"))
        seq2 = []
        for _ in range(6):
            seq2.append(badge(sw))
            time.sleep(0.5)
        after2 = len(field_text(page, "#ta"))
        dbg_f2 = sw.evaluate("() => globalThis.__typeclipDbg()")
        ok_f2 = mid2 == after2 and all(x == "" for x in seq2) and "cancelado por el usuario" in " ".join(dbg_f2)
        report("F) cancelación por re-invocación (toggle)", ok_f2,
               f"mid={mid2} after={after2} seq={seq2}")
        page.bring_to_front()
        time.sleep(0.3)
        # Prueba de detach real: un tipeo nuevo debe volver a usar CDP.
        set_settings(sw)
        prep(page, "#inp", "simple")
        invoke(sw)
        ok = wait_value(page, "#inp", PAYLOADS["simple"], 30000)
        tip = badge_tooltip(sw)
        report("F) detach limpio (re-tipeo vía CDP de nuevo)", ok and "CDP" in tip,
               f"badge={badge(sw)!r} tip={tip[:70]!r}")

        # ---------------- G) página chrome:// → ERR sin crashear ---------------
        # Nota: el atajo NO se puede probar con teclado sintético en headless
        # (los comandos de extensión no disparan), así que se invoca la misma
        # función que ejecutaría el comando, con la pestaña chrome:// activa.
        page2 = ctx.new_page()
        page2.goto("chrome://version", wait_until="load")
        page2.bring_to_front()
        time.sleep(0.5)
        invoke(sw)
        time.sleep(1.5)
        b = badge(sw)
        det = f"badge={b!r} tip={badge_tooltip(sw)[:80]!r}"
        if b != "ERR":
            det += "\nDBG SW: " + " || ".join(sw.evaluate("() => globalThis.__typeclipDbg()")[-12:])
        report("G) chrome:// rechazado con ERR", b == "ERR", det)
        page2.close()
        page.bring_to_front()
        time.sleep(0.4)

        # ---------------- H) cambio de pestaña a mitad del tipeo ---------------
        # La activación se hace con chrome.tabs.update DESDE EL SW (nivel browser,
        # no encolado detrás del debugger de la pestaña): es un cambio de pestaña
        # REAL que dispara tabs.onActivated → abort.
        set_settings(sw, wpm=250, pauses=False)
        prep(page, "#ta", "largo")
        invoke(sw)
        time.sleep(2.5)
        sw.evaluate("""() => chrome.tabs.create({ url: 'about:blank' }).then(t =>
            chrome.tabs.update(t.id, { active: true }))""")
        time.sleep(2.5)
        dbg_h = sw.evaluate("() => globalThis.__typeclipDbg()")
        b = badge(sw)
        mid = len(field_text(page, "#ta"))  # el abort detachea → eval destrabado
        time.sleep(1.5)
        after = len(field_text(page, "#ta"))
        det = f"mid={mid} after={after} badge={b!r} tip={badge_tooltip(sw)[:70]!r}"
        ok_h = mid == after and b == "ERR" and any("pestaña" in x or "abort" in x for x in dbg_h)
        if not ok_h:
            det += "\nDBG SW: " + " || ".join(dbg_h[-15:])
        report("H) abort por cambio de pestaña", ok_h, det)
        # cerrar la pestaña nueva y volver a la de prueba
        sw.evaluate("""() => chrome.tabs.query({}).then(ts => {
            const mine = chrome.runtime.getURL('');
            return Promise.all(ts.filter(t => (t.url || '').startsWith('about:blank'))
              .map(t => chrome.tabs.remove(t.id)));
          })""")
        page.bring_to_front()
        time.sleep(0.4)

        # ---------------- I) typos ON → se corrigen solos ----------------------
        set_settings(sw, wpm=220, pauses=False, typos=True, typoPct=25)
        prep(page, "#inp", "simple")
        invoke(sw)
        ok = wait_value(page, "#inp", PAYLOADS["simple"], 45000)
        bs = page.evaluate("() => (window.__events||[]).filter(r => r.type==='keydown' && r.key==='Backspace').length")
        report("I) typos simulados y corregidos", ok and bs > 0, f"backspaces={bs} texto_final_ok={ok}")

        # ---------------- J) FALLBACK 1 forzado: eventos JS + execCommand -----
        # Se neutraliza chrome.debugger.attach DENTRO del SW (simula "sin
        # permiso de debugger / attach falla"). El texto debe entrar igual,
        # con eventos sintéticos isTrusted=false (documentado en el README).
        set_settings(sw)
        sw.evaluate("() => { globalThis.__origAttach = chrome.debugger.attach;"
                    "  chrome.debugger.attach = async () => { throw new Error('e2e: sin debugger'); }; }")
        prep(page, "#ta", "x280")
        invoke(sw)
        ok = wait_value(page, "#ta", PAYLOADS["x280"], 90000)
        b, tip = badge(sw), badge_tooltip(sw)
        report("J) fallback JS — texto completo", ok, "" if ok else f"quedó: {field_text(page, '#ta')[:80]!r}")
        report("J) fallback JS — badge/método", b == "OK" and "JS" in tip, f"badge={b!r} tip={tip[:70]!r}")
        # Los keydown/keypress sintéticos son isTrusted=false (documentado); los
        # `input` que dispara execCommand("insertText") los genera el browser y
        # son isTrusted=true. Lo que NO puede haber es paste, ni data de >1 cp.
        untrusted = page.evaluate("() => (window.__events||[]).filter(r => r.type==='keydown' && !r.isTrusted).length")
        pastes = page.evaluate("() => (window.__events||[]).filter(r => r.type==='paste').length")
        multi = page.evaluate("() => (window.__events||[])"
                              ".filter(r => (r.type==='input'||r.type==='beforeinput')"
                              " && r.data !== null && Array.from(r.data).length !== 1).length")
        report("J) fallback JS — sin paste, 1 cp por evento, keydown sintéticos",
               pastes == 0 and multi == 0 and untrusted > 0,
               f"paste={pastes} data_multicp={multi} keydown_no_trusted={untrusted}")
        # Sin beforeinput SINTÉTICO: antes del fix se disparaba uno propio por
        # caracter (isTrusted=false) y en editores que hacen
        # preventDefault(beforinput) el caracter entraba DOS veces. Ahora van
        # solo los nativos que genere execCommand (en textarea dispara input;
        # el beforeinput del editing engine, donde lo emita).
        bi_j = page.evaluate("() => (window.__events||[]).filter(r => r.type==='beforeinput').length")
        bi_synth = page.evaluate("() => (window.__events||[]).filter(r => r.type==='beforeinput' && !r.isTrusted).length")
        in_j = page.evaluate("() => (window.__events||[]).filter(r => r.type==='input').length")
        report("J) fallback JS — sin beforeinput sintético",
               bi_synth == 0 and in_j > 0 and bi_j <= in_j,
               f"beforeinput={bi_j} ({bi_synth} sintéticos) input={in_j}")

        # ---------------- K) FALLBACK 2 forzado: setter nativo -----------------
        # execCommand anulado EN LA PÁGINA (válido: en la página de la extensión
        # el content script corre en el mismo mundo) → cada caracter cae al
        # setter nativo + evento input manual, un code point por vez.
        page.evaluate("() => { document.execCommand = () => false; }")
        prep(page, "#ce", "x280")
        invoke(sw)
        got = wait_stable(page, "#ce", 90000)
        # innerText de un contenteditable con pre-wrap agrega un \n final propio
        # del DOM (por eso la extensión normaliza con trim): comparar sin él.
        ok = norm(got).rstrip("\n") == norm(PAYLOADS["x280"]).rstrip("\n")
        b, tip = badge(sw), badge_tooltip(sw)
        report("K) fallback SET — texto completo (contenteditable)", ok,
               "" if ok else f"{first_diff(norm(got), norm(PAYLOADS['x280']))}")
        report("K) fallback SET — método JS/SET", "SET" in tip, f"badge={b!r} tip={tip[:70]!r}")
        sw.evaluate("() => { chrome.debugger.attach = globalThis.__origAttach; }")
        page.reload(wait_until="load")
        page.wait_for_timeout(500)

        # ---------------- L) input de una línea en <form>: NUNCA submit -------
        # Regla "nunca hace submit de formularios": un Enter real (CDP keyDown
        # con text "\r") en un <input> de una línea dispara el default action
        # de Chrome — submit del form que lo contenga (verificado empíricamente
        # antes del fix: log = ['kd:Enter', 'change', 'submit']). Con payload
        # multi-línea la extensión debe colapsar los saltos a UN espacio y no
        # despachar ningún Enter.
        set_settings(sw)
        prep(page, "#inp", "multiline")
        invoke(sw)
        expected_ml = re.sub(r"\n+", " ", PAYLOADS["multiline"].replace("\r\n", "\n").replace("\r", "\n"))
        ok = wait_value(page, "#inp", expected_ml, 60000)
        submits = page.evaluate("() => (window.__events||[]).filter(r => r.type === 'submit').length")
        enters = page.evaluate("() => (window.__events||[]).filter(r => r.type === 'keydown' && r.key === 'Enter').length")
        b, tip = badge(sw), badge_tooltip(sw)
        det = ("" if ok else f"quedó: {field_text(page, '#inp')!r} · ")
        det += f"submits={submits} enters={enters} badge={b!r}"
        report("L) input en form — multi-línea sin submit ni Enter", ok and submits == 0 and enters == 0, det)
        report("L) input en form — badge OK (saltos→espacios, método CDP)",
               b == "OK" and "CDP" in tip, f"badge={b!r} tip={tip[:70]!r}")

        # ---------------- M) timeStamp de los eventos CDP ----------------------
        # Los keydown/input que genera TypeClip deben tener un e.timeStamp
        # coherente con performance.now(). Antes del fix se enviaba
        # timestamp: Date.now() (ms) donde CDP espera segundos-epoch → el
        # timeStamp del sitio quedaba ~1.7e15 ms a futuro (medido).
        set_settings(sw)
        prep(page, "#ta", "simple")
        page.evaluate("""() => {
          window.__ts = [];
          const ta = document.getElementById('ta');
          for (const t of ['keydown', 'input']) ta.addEventListener(t, (e) => {
            if (e.isTrusted) window.__ts.push(e.timeStamp - performance.now());
          }, { capture: true });
        }""")
        invoke(sw)
        ok = wait_value(page, "#ta", PAYLOADS["simple"], 30000)
        time.sleep(0.5)
        ts = page.evaluate("() => window.__ts || []")
        max_d = max((abs(d) for d in ts), default=1e18)
        report("M) timeStamp coherente (CDP)", ok and len(ts) > 10 and max_d < 1000,
               f"{len(ts)} eventos, |delta| máx={max_d:.1f} ms")

        # ---------------- N) campo con texto previo (caret al final) -----------
        # Línea base: el campo ya tenía texto → el badge tiene que ser OK (el
        # tipeo quedó insertado) y no DIF eterno, y sin duplicar especiales.
        prep(page, "#ta", "especiales")
        page.eval_on_selector("#ta", "el => { el.value = 'antes: '; el.setSelectionRange(7, 7); }")
        invoke(sw)
        got = wait_stable(page, "#ta", 60000)
        time.sleep(1)
        b, tip = badge(sw), badge_tooltip(sw)
        exp_n = "antes: " + PAYLOADS["especiales"]
        report("N) campo con texto previo — inserta completo y sin duplicar",
               norm(got) == norm(exp_n) and got.count("ñ") == 3,
               "" if norm(got) == norm(exp_n) else f"quedó: {got!r}")
        report("N) campo con texto previo — badge OK (verifica contra línea base)",
               b == "OK" and "ya tenía texto" in tip, f"badge={b!r} tip={tip[:80]!r}")

        # ---------------- O) caret en el medio + caracteres especiales ---------
        # La sonda vieja miraba la COLA del campo (asumía caret al final) y
        # duplicaba la primera ñ/¿/¡/é. Ahora compara largos antes/después.
        prep(page, "#ta", "especiales")
        page.eval_on_selector("#ta", "el => { el.value = 'abcdef'; el.setSelectionRange(3, 3); }")
        invoke(sw)
        got = wait_stable(page, "#ta", 60000)
        exp_o = "abc" + PAYLOADS["especiales"] + "def"
        report("O) caret en el medio — sin duplicar ñ ¿ ¡ é",
               norm(got) == norm(exp_o),
               "" if norm(got) == norm(exp_o) else f"quedó: {got!r} esperado: {exp_o!r}")

        # ---------------- P) editor async (inserta 60 ms después) --------------
        # #xce2 cancela el beforeinput y aplica el texto 60 ms después (render
        # diferido tipo Lexical/ProseMirror). La sonda debe ESPERAR ese delay;
        # si lee en el acto, cae a insertText y el caracter entra dos veces.
        prep(page, "#xce2", "especiales")
        invoke(sw)
        got = wait_stable(page, "#xce2", 60000)
        exp_p = PAYLOADS["especiales"]
        ok_p = norm(got).rstrip("\n") == norm(exp_p).rstrip("\n")
        report("P) editor async — la sonda espera el render diferido",
               ok_p, "" if ok_p else f"quedó: {got!r} esperado: {exp_p!r}")
    finally:
        ctx.close()
        httpd.shutdown()

    log("\n=== RESUMEN ===")
    for name, ok, detail in results:
        log(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    fails = sum(1 for _, ok, _ in results if not ok)
    log(f"\n{len(results) - fails}/{len(results)} PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
