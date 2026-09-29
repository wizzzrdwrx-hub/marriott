# Photon Forcer Generator

A standalone visualization prompt generator. Open `index.html` in a browser;
the application has no build step or runtime dependencies.

## Verification

Use Python 3.10 or later:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium --only-shell
python -m unittest discover -s tests -v
python verify.py
python verify_screenshot.py
```

On Linux, Playwright may require `python -m playwright install --with-deps
chromium --only-shell` to install browser system dependencies. The screenshot
is written to `verification/index_verification.png`.

Tests load the real `index.html` in Chromium. They cover prompt formatting,
all subject defaults and negative prompts, live form updates, reset, literal
user text, clipboard success/rejection/absence/insecure contexts, fallback
false/exception cleanup and focus restoration, and overlapping toast timers.
Clipboard APIs are stubbed to deterministically exercise failure paths; these
tests do not establish OS clipboard permission behavior in every browser.

GitHub Actions runs the suite on pull requests and default-branch pushes.

## Clipboard compatibility

The modern Clipboard API remains the preferred path. The existing
`execCommand('copy')` fallback is retained for restricted or insecure contexts.
It can fail or be unavailable in browsers; failure feedback remains visible,
and users can select and copy the output manually. Temporary copy controls are
removed and focus is restored regardless of the fallback result.
