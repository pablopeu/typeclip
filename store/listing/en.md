# Chrome Web Store listing — English (primary language)

## Name

TypeClip

## Summary (short description, ≤132 chars — dashboard field)

Types the text you copied, key by key with real keyboard events, into the
field you choose. Nothing is stored or sent anywhere.

*(127 characters — verified.)*

## Category

**Productivity.** Justification: TypeClip is a text-entry utility — it saves
typing work in fields where you paste text often (post composers, forms,
email). Among the CWS categories (Productivity, Developer Tools,
Accessibility, Fun, …) Productivity is the standard home for typing/clipboard
utilities and matches what a user would search for. (Accessibility was
considered: it *can* help users who type slowly, but its primary framing is
productivity, not assistive technology.)

## Single purpose (dashboard field)

Types text from the clipboard into the focused field, key by key, on the
user's explicit command.

## Long description (dashboard field)

TypeClip types for you the text you copied.

Copy as usual (Ctrl+C), click the field where you want it — a post composer,
a form, an email — and TypeClip writes it character by character, with
human-like timing, as if you were typing it yourself. The page receives real
keyboard events, which also makes it useful in fields that block or restrict
pasting.

• Real keyboard events, via Chrome's debugging protocol. While it types,
Chrome shows its "controlled by automated test software" banner — that is
expected, it disappears on its own when the text is done, and the debugger is
released immediately.

• Human rhythm: base speed, natural variation, small pauses; optionally it
even makes typing mistakes and corrects them with Backspace, like a person.

• Privacy first: the text is read from the clipboard only at the moment you
run TypeClip, lives only in memory, and is never stored or sent anywhere. No
analytics, no third parties, no remote code.

• You stay in control: it never presses Post or Send, never submits forms,
and never changes your focus. Esc (or running it again) cancels immediately,
leaving what was already typed.

• Works in any editable field of a web page: single-line inputs, textareas
and rich contenteditable editors. Sites with their own pop-up editors may
behave differently; check the OK / DIF badge on the icon when it finishes.

• Configurable: speed, pauses, mistakes, Tab handling — and the options page
is in English and Spanish.

Limitations: desktop Chrome only (no phones). If the field has a maximum
length, the text stops at the limit. The yellow banner while typing is part
of how real keyboard events work in Chrome.

Source code: github.com/pablopeu/typeclip

## Justification of each permission

| Permission | Why TypeClip needs it |
|---|---|
| `debugger` | Sends the real keyboard events (key by key) into the focused field using Chrome's DevTools protocol. Attached only while typing on the tab you invoked it from; detached the instant typing ends or you cancel. This is the core of the extension — without it the events would not be real keyboard events. |
| `clipboardRead` | Reads the text you copied, only at the exact moment you run TypeClip. Nothing else is ever read; the text stays in memory. |
| `offscreen` | MV3 service workers cannot touch the clipboard. A hidden offscreen document reads it and passes the text to the service worker in memory. It exists only for the seconds of a run. |
| `activeTab` | Limits every operation to the tab you explicitly invoked TypeClip on. No broad host access is requested or wanted. |
| `scripting` | Injects the small content script into the active tab's frames — to find the focused editable field and to run the in-page fallback if the debugger cannot attach. |
| `storage` | Saves your options (speed, language, etc.) in `chrome.storage.sync`. Only settings are stored — never typed text. |

## Does it use remote code? (dashboard field)

**No.** All logic ships inside the package; there are no network requests of
any kind (verifiable with `tools/audit.py` in the repository).

## URLs

- Homepage: https://github.com/pablopeu/typeclip
- Support: https://github.com/pablopeu/typeclip/issues
- Privacy policy: https://pablopeu.github.io/typeclip/privacy.html
  (requires enabling GitHub Pages on `/docs` — see SUBMISSION_CHECKLIST.md;
  fallback while that is set up: https://github.com/pablopeu/typeclip/blob/main/PRIVACY.md)

## Instructions for the reviewer

1. Load the extension (extract the ZIP and "Load unpacked" the extracted
   folder — `manifest.json` is at its root —, or install it from this item)
   with Developer mode in `chrome://extensions`.
2. Open the demo page: https://pablopeu.github.io/typeclip/demo.html
   (if GitHub Pages is not enabled yet, open `docs/demo.html` from the
   repository locally, served over any http:// URL).
3. Copy any text (Ctrl+C), click any field on that page and press
   Alt+Shift+V (or click the TypeClip toolbar icon).
4. Expected: the text is typed character by character with irregular timing;
   the icon badge shows progress (a percentage) and ends in a green **OK**. The
   yellow "automated test software" banner appears while typing and
   disappears by itself at the end.
5. Cancel path: run it again and press Esc mid-typing — it stops instantly
   and the banner goes away.
6. Options: right-click the icon → Options (English by default, Spanish
   switch on the top right).
7. Source code and an automated 37-check E2E suite are in the repository
   (`tools/e2e.py`).

## Data use disclosures (dashboard privacy fields) — PROPOSED, owner to confirm

- **User-generated content** (the clipboard text, handled in memory and typed
  into the field): **declared**. The CWS User Data FAQ states that data
  processed locally, never transmitted, still counts as "handled" and must be
  disclosed — so we declare it even though nothing leaves the device.
- Sale of data: **No**. Use for purposes unrelated to the single purpose:
  **No**. Use for creditworthiness: **No** (Limited Use compliant).
- No authentication, financial, health, browsing-history or communications
  data is collected. The options saved in `chrome.storage.sync` are the
  user's own settings, synced by Chrome itself.
- DECISIÓN PENDIENTE (owner): whether to also declare "Website content"
  (the extension reads the focused field's current content, in memory, to
  verify the result). Our reading is that it is the same user content, but
  the conservative option is to declare both.
