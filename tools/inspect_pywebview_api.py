r"""
Tiny inspection helper to print the installed pywebview API surface.

Run:
  .\.venv\Scripts\python tools\inspect_pywebview_api.py
"""

import inspect

import webview


def main() -> None:
    print("pywebview version:", getattr(webview, "__version__", "unknown"))
    print()

    print("create_window signature:")
    try:
        print(inspect.signature(webview.create_window))
    except Exception as e:
        print("  <unable to get signature>", e)
    print()

    print("create_window doc:")
    doc = inspect.getdoc(webview.create_window) or ""
    print(doc[:2000])
    if len(doc) > 2000:
        print("... (truncated)")


if __name__ == "__main__":
    main()

