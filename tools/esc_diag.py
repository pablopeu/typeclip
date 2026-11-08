#!/usr/bin/python3
"""Repro del camino Esc→cancel: invoca un tipeo largo, aprieta Escape con
teclado de Playwright y verifica los tres eslabones:
 1) la página recibió keydown Escape (window.__events)
 2) el SW recibió el mensaje 'esc' y canceló (ring-buffer __typeclipDbg)
 3) el tipeo se cortó (largo del campo) y el badge quedó limpio."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def main():
    ctx = sync_playwright().start().chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-esc-"),
        channel="chromium", headless=True,
        args=[f"--disable-extensions-except={e2e.EXT}", f"--load-extension={e2e.EXT}", "--window-size=1400,1000"],
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
        assert sw

        page.goto(sw.evaluate("() => chrome.runtime.getURL('test/index.html')"), wait_until="load")
        e2e.set_settings(sw, wpm=250, pauses=False)
        e2e.prep(page, "#ta", "largo")
        e2e.invoke(sw)
        time.sleep(2.0)
        n0 = len(e2e.field_text(page, "#ta"))
        page.keyboard.press("Escape")
        time.sleep(1.5)
        n1 = len(e2e.field_text(page, "#ta"))
        time.sleep(1.5)
        n2 = len(e2e.field_text(page, "#ta"))

        esc_ev = page.evaluate("() => (window.__events||[]).filter(r => r.key === 'Escape').length")
        esc_trusted = page.evaluate("() => (window.__events||[]).filter(r => r.key === 'Escape' && r.isTrusted).length")
        dbg = sw.evaluate("() => globalThis.__typeclipDbg()")
        badge_now = e2e.badge(sw)
        print(f"campo: n0={n0} n1(tras Esc+1.5s)={n1} n2(+3s)={n2}")
        print(f"eventos Escape en la página: {esc_ev} (trusted: {esc_trusted})")
        print(f"badge: {badge_now!r}")
        print("dbg tail:")
        for ln in dbg[-8:]:
            print("   ", ln)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
