#!/usr/bin/python3
"""Ver la línea de comandos real del Chrome lanzado por Playwright."""
import tempfile, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

EXT = Path(__file__).resolve().parent.parent / "typeclip"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-smoke-"),
        channel="chrome", headless=True,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
        viewport=None,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("about:blank")
    page.wait_for_timeout(800)
    pid = page.evaluate("() => navigator.userAgent")
    out = subprocess.run(["pgrep", "-af", "chrome"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "--load-extension" in line or "--headless" in line or "--disable-extensions" in line:
            print(line[:600])
            print("---")
    ctx.close()
