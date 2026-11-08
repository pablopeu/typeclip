#!/usr/bin/python3
"""Smoke test con ignore_default_args=['--disable-extensions']."""
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

EXT = Path(__file__).resolve().parent.parent / "typeclip"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=tempfile.mkdtemp(prefix="tc-smoke-"),
        channel="chrome", headless=True,
        ignore_default_args=["--disable-extensions"],
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
        viewport=None,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("http://example.org", wait_until="domcontentloaded")
    sw = None
    for _ in range(50):
        for w in ctx.service_workers:
            if "background" in (w.url or ""):
                sw = w
        if sw:
            break
        page.wait_for_timeout(200)
    print("SW:", sw.url if sw else "NO ENCONTRADO")
    if sw:
        print("focused:", sw.evaluate("() => chrome.windows.getLastFocused().then(w => [w.id, w.focused])"))
        print("attach:", sw.evaluate(
            "() => chrome.tabs.query({active:true,currentWindow:true}).then(async ([t]) => {"
            "  try { await chrome.debugger.attach({tabId: t.id}, '1.3'); } catch (e) { return 'ERR: ' + e.message; }"
            "  await new Promise(r => setTimeout(r, 300));"
            "  try { await chrome.debugger.detach({tabId: t.id}); return 'ATTACH+DETACH OK'; }"
            "  catch (e) { return 'DETACH ERR: ' + e.message; }"
            "})"))
        print("clipboard(offscreen):", sw.evaluate(
            "() => (async () => {"
            "  try { await chrome.offscreen.createDocument({url:'offscreen.html', reasons:['CLIPBOARD'], justification:'smoke'}); } catch(e) {}"
            "  const r = await new Promise(res => { const t=setTimeout(()=>res({ok:false,error:'timeout'}),3000);"
            "    chrome.runtime.sendMessage({tc:'read-clipboard'}, resp => { clearTimeout(t); res(resp); }); });"
            "  try { await chrome.offscreen.closeDocument(); } catch(e) {}"
            "  return r; })()"))
    ctx.close()
