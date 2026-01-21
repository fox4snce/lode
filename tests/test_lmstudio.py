import pytest

# Manual integration script (requires LM Studio running locally).
pytest.skip("manual integration script (requires LM Studio)", allow_module_level=True)

"""
Quick test against LM Studio's OpenAI-compatible endpoint.

Run:
  python test_lmstudio.py

Prereq:
  LM Studio server running at http://127.0.0.1:1234
"""

from lmstudio_llm import chat_completions


def main() -> int:
    text = chat_completions(
        model=None,
        messages=[
            {"role": "system", "content": "Always answer in rhymes."},
            {"role": "user", "content": "Introduce yourself."},
        ],
        temperature=0.7,
        max_tokens=-1,
        stream=True,
        print_stream=True,
    )
    print("\n---\nFULL RESPONSE:\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


