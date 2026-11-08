#!/usr/bin/python3
"""Diagnóstico dedicado del subtest E (2000+ caracteres): reproduce E en soledad
y captura evidencia forense — texto final del campo, log de eventos de la página
(keydown/input con data e isTrusted) y ring-buffer de control del service worker.
Reusa los helpers del arnés e2e.py. Correr DESPUÉS de que termine un e2e.py vivo
(los dos usan el mismo portapapeles/headless; mejor sin contención de timing)."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e  # noqa: E402  (helpers: PAYLOADS, norm, field_text, badge, set_settings, invoke, prep, wait_value, first_diff)
from playwright.sync_api import sync_playwright  # noqa: E402


def main():
    ext = e2e.EXT
    ctx = sync_playwright().start().chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-ediag-"),
        channel="chromium", headless=True,
        args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}", "--window-size=1400,1000"],
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
        assert sw, "no apareció el service worker"

        ext_page = sw.evaluate("() => chrome.runtime.getURL('test/index.html')")
        page.goto(ext_page, wait_until="load")
        e2e.set_settings(sw, wpm=250, jitter=10, pauses=False, thinkPct=0)
        e2e.prep(page, "#ta", "largo")
        t0 = time.time()
        e2e.invoke(sw)
        ok = e2e.wait_value(page, "#ta", e2e.PAYLOADS["largo"], 900000, interval=1.5)
        dur = time.time() - t0
        b = e2e.badge(sw)
        got = e2e.field_text(page, "#ta")
        print(f"[{'PASS' if ok else 'FAIL'}] E-diag {len(e2e.PAYLOADS['largo'])} chars en {dur:.0f}s badge={b!r}")
        if not ok:
            print("   ", e2e.first_diff(e2e.norm(got), e2e.norm(e2e.PAYLOADS["largo"])))
            e2e.dump_evidence(page, sw, "diag")
        else:
            # igual volcamos el dbg del SW para ver la línea de tiempo de probes
            dbg = sw.evaluate("() => globalThis.__typeclipDbg ? globalThis.__typeclipDbg() : ['sin dbg']")
            Path("/tmp/e-diag-swdbg.txt").write_text("\n".join(dbg))
            print("    dbg en /tmp/e-diag-swdbg.txt")
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
