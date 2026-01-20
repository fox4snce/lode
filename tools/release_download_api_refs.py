#!/usr/bin/env python3
"""
Release helper: download API reference pages/specs for offline review (not committed).

Why:
  - During release, it's useful to snapshot the current provider API docs/specs and
    sanity-check that our usage hasn't drifted.

Notes:
  - This script does NOT assume specific URLs (so we don't "guess").
  - Provide the URLs explicitly (e.g. official API reference pages or OpenAPI specs).
  - Output goes to docs/ignored/api_refs/ (gitignored).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
from urllib.request import Request, urlopen


def _download(url: str, out_path: Path) -> dict:
    req = Request(
        url,
        headers={
            # Some doc sites block default Python UA.
            "User-Agent": "LodeReleaseBot/1.0 (+local release script)",
            "Accept": "*/*",
        },
    )
    with urlopen(req, timeout=60) as resp:
        data = resp.read()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        headers = dict(resp.headers.items())
    return headers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai-url", default=os.getenv("LODE_RELEASE_OPENAI_DOC_URL", "").strip())
    parser.add_argument("--anthropic-url", default=os.getenv("LODE_RELEASE_ANTHROPIC_DOC_URL", "").strip())
    parser.add_argument("--out-dir", default="docs/ignored/api_refs")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not args.openai_url and not args.anthropic_url:
        print("No URLs provided.")
        print("Provide --openai-url and/or --anthropic-url, or set:")
        print("  - LODE_RELEASE_OPENAI_DOC_URL")
        print("  - LODE_RELEASE_ANTHROPIC_DOC_URL")
        return 2

    if args.openai_url:
        out = out_dir / f"openai_{ts}.bin"
        headers = _download(args.openai_url, out)
        print(f"[OpenAI] Saved: {out}")
        print(f"[OpenAI] URL: {args.openai_url}")
        if "Last-Modified" in headers:
            print(f"[OpenAI] Last-Modified: {headers['Last-Modified']}")
        if "ETag" in headers:
            print(f"[OpenAI] ETag: {headers['ETag']}")
        print()

    if args.anthropic_url:
        out = out_dir / f"anthropic_{ts}.bin"
        headers = _download(args.anthropic_url, out)
        print(f"[Anthropic] Saved: {out}")
        print(f"[Anthropic] URL: {args.anthropic_url}")
        if "Last-Modified" in headers:
            print(f"[Anthropic] Last-Modified: {headers['Last-Modified']}")
        if "ETag" in headers:
            print(f"[Anthropic] ETag: {headers['ETag']}")
        print()

    print("Done. (These files are intended to stay local; do not commit.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

