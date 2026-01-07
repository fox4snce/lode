"""
Lode desktop launcher entrypoint.

IMPORTANT:
- This file is the entrypoint users run: `python launcher.py`
- It delegates to the real desktop launcher in `app/launcher.py`

Why:
- The repo previously had an older launcher that used `api/main.py` and served
  legacy `/static/...` assets. That caused 404s like `/static/js/app.js` and made
  UI changes appear to "not work".
"""

from app.launcher import main


if __name__ == "__main__":
    print("Lode: using desktop launcher at `app/launcher.py` (Jinja2/HTMX + FastAPI).")
    main()

