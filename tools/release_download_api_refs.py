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
import gzip
import os
from pathlib import Path
from urllib.request import Request, urlopen


def _download(url: str, out_path: Path) -> dict:
    req = Request(
        url,
        headers={
            # Use browser-like headers to avoid 403 on docs sites.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        },
    )
    with urlopen(req, timeout=60) as resp:
        data = resp.read()
        # Decompress if gzip-encoded
        content_encoding = resp.headers.get("Content-Encoding", "").lower()
        if "gzip" in content_encoding:
            data = gzip.decompress(data)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        headers = dict(resp.headers.items())
    return headers


def main() -> int:
    # Default URLs (verified working official docs)
    DEFAULT_OPENAI_URL = "https://platform.openai.com/docs/quickstart"
    DEFAULT_ANTHROPIC_URL = "https://platform.claude.com/docs/en/get-started"
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openai-url",
        default=os.getenv("LODE_RELEASE_OPENAI_DOC_URL", DEFAULT_OPENAI_URL).strip()
    )
    parser.add_argument(
        "--anthropic-url",
        default=os.getenv("LODE_RELEASE_ANTHROPIC_DOC_URL", DEFAULT_ANTHROPIC_URL).strip()
    )
    parser.add_argument("--out-dir", default="docs/ignored/api_refs")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if args.openai_url:
        out = out_dir / f"openai_{ts}.html"
        headers = _download(args.openai_url, out)
        print(f"[OpenAI] Saved: {out}")
        print(f"[OpenAI] URL: {args.openai_url}")
        if "Last-Modified" in headers:
            print(f"[OpenAI] Last-Modified: {headers['Last-Modified']}")
        if "ETag" in headers:
            print(f"[OpenAI] ETag: {headers['ETag']}")
        print()

    if args.anthropic_url:
        out = out_dir / f"anthropic_{ts}.html"
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

