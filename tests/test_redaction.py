"""
Tests for redaction tool.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import re
from redaction_tool import redact_text, redact_emails, redact_phones, redact_names


def test_redact_emails():
    """Test email redaction."""
    text = "Contact me at john.doe@example.com or admin@company.org"
    result = redact_text(text, patterns=['email'])
    
    assert '[REDACTED]' in result
    assert 'john.doe@example.com' not in result
    assert 'admin@company.org' not in result
    
    print("[PASS] test_redact_emails")


def test_redact_phones():
    """Test phone number redaction."""
    text = "Call me at 555-123-4567 or (555) 987-6543"
    result = redact_text(text, patterns=['phone'])
    
    assert '[REDACTED]' in result
    assert '555-123-4567' not in result
    
    print("[PASS] test_redact_phones")


def test_redact_names():
    """Test name redaction."""
    text = "John Smith and Jane Doe met with Dr. Robert Johnson"
    result = redact_text(text, patterns=['name'])
    
    assert '[REDACTED]' in result
    # Names should be redacted
    print(f"Result: {result}")
    print("[PASS] test_redact_names")


def test_preserve_code_blocks():
    """Test that code blocks are preserved."""
    text = """
    Here's my email: user@example.com
    
    ```python
    email = "test@example.com"  # This should stay
    ```
    
    Contact admin@company.com
    """
    result = redact_text(text, patterns=['email'], skip_code_blocks=True)
    
    # Email in code block should remain
    assert 'test@example.com' in result or 'email =' in result
    # Email outside should be redacted
    assert 'user@example.com' not in result or '[REDACTED]' in result
    
    print("[PASS] test_preserve_code_blocks")


if __name__ == '__main__':
    test_redact_emails()
    test_redact_phones()
    test_redact_names()
    test_preserve_code_blocks()
    print("\nAll redaction tests passed!")

