#!/usr/bin/python3
"""Repro Esc v2: telemetría completa de quién escribe #ta y cuándo.
Muestrea len(#ta), len(#copybuf), activeElement y conteo de eventos cada 0,5 s
durante 6 s tras invoke; luego Esc; al final vuelca todo el dbg del SW."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2e  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def snapshot(page):
    return page.evaluate("""() => ({
      ta: (document.getElementById('ta').value || '').length,
      copybuf: (document.getElementById('copybuf').value || '').length,
      ae: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : 'none',
      ev: (window.__events||[]).length,
      evInput: (window.__events||[]).filter(r => r.type==='input').length,
      evPaste: (window.__events||[]).filter(r => r.type==='paste').length,
    })""")


def main():
    ctx = sync_playwright().start().chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-esc2-"),
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
        print("tras prep:", snapshot(page))
        e2e.invoke(sw)
        for k in range(12):
            time.sleep(0.5)
            print(f"t+{(k+1)*0.5:4.1f}s", snapshot(page))
        page.keyboard.press("Escape")
        for k in range(4):
            time.sleep(0.5)
            print(f"esc+{(k+1)*0.5:4.1f}s", snapshot(page))
        print("badge:", repr(e2e.badge(sw)))
        Path("/tmp/esc2-swdbg.txt").write_text("\n".join(sw.evaluate("() => globalThis.__typeclipDbg()")))
        print("dbg completo en /tmp/esc2-swdbg.txt")
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
