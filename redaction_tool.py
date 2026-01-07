"""
Redaction tool for removing sensitive information.

Replaces emails, phone numbers, and names with [REDACTED].
"""
import re
import sqlite3
from typing import List, Optional, Dict


DB_PATH = 'conversations.db'

# Regex patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
NAME_PATTERN = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+ [A-Z][a-z]+\b|\b[A-Z][a-z]+ [A-Z][a-z]+\b')


def redact_emails(text: str) -> str:
    """Redact email addresses."""
    return EMAIL_PATTERN.sub('[REDACTED]', text)


def redact_phones(text: str) -> str:
    """Redact phone numbers."""
    return PHONE_PATTERN.sub('[REDACTED]', text)


def redact_names(text: str) -> str:
    """Redact names (First Last pattern)."""
    # More conservative: only redact if it looks like a full name
    # This is a simple heuristic and may have false positives/negatives
    return NAME_PATTERN.sub('[REDACTED]', text)


def extract_code_blocks(text: str) -> List[Dict]:
    """Extract code blocks from text."""
    blocks = []
    pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
    
    for match in pattern.finditer(text):
        blocks.append({
            'full_match': match.group(0),
            'language': match.group(1) or '',
            'content': match.group(2),
            'start': match.start(),
            'end': match.end()
        })
    
    return blocks


def redact_text(
    text: str,
    patterns: Optional[List[str]] = None,
    skip_code_blocks: bool = True
) -> str:
    """
    Redact sensitive information from text.
    
    Args:
        text: Input text
        patterns: List of patterns to redact ('email', 'phone', 'name')
                 If None, redacts all
        skip_code_blocks: If True, don't redact inside code blocks
    
    Returns:
        Redacted text
    """
    if patterns is None:
        patterns = ['email', 'phone', 'name']
    
    if skip_code_blocks:
        # Extract and protect code blocks
        code_blocks = extract_code_blocks(text)
        placeholders = {}
        
        # Replace code blocks with placeholders
        protected_text = text
        for i, block in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            placeholders[placeholder] = block['full_match']
            protected_text = protected_text.replace(block['full_match'], placeholder, 1)
        
        # Redact the protected text
        result = protected_text
        if 'email' in patterns:
            result = redact_emails(result)
        if 'phone' in patterns:
            result = redact_phones(result)
        if 'name' in patterns:
            result = redact_names(result)
        
        # Restore code blocks
        for placeholder, original in placeholders.items():
            result = result.replace(placeholder, original)
        
        return result
    else:
        # Simple redaction without code block protection
        result = text
        if 'email' in patterns:
            result = redact_emails(result)
        if 'phone' in patterns:
            result = redact_phones(result)
        if 'name' in patterns:
            result = redact_names(result)
        return result


def redact_conversation(
    db_path: str,
    conversation_id: str,
    output_path: Optional[str] = None,
    patterns: Optional[List[str]] = None,
    skip_code_blocks: bool = True
) -> str:
    """
    Redact a conversation and optionally export it.
    
    Args:
        db_path: Database path
        conversation_id: Conversation ID
        output_path: Optional file path to write redacted version
        patterns: Patterns to redact
        skip_code_blocks: Skip redaction in code blocks
    
    Returns:
        Redacted markdown content
    """
    from export_tools import export_conversation_to_markdown
    
    # Export to markdown first
    markdown = export_conversation_to_markdown(
        db_path, conversation_id,
        include_timestamps=True,
        include_metadata=True
    )
    
    # Redact the markdown
    redacted = redact_text(markdown, patterns=patterns, skip_code_blocks=skip_code_blocks)
    
    # Write to file if requested
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(redacted)
    
    return redacted


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python redaction_tool.py <command> [args...]")
        print("\nCommands:")
        print("  text <text> [patterns]")
        print("  conversation <conversation_id> [output.md] [patterns]")
        print("\nPatterns: email, phone, name (default: all)")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'text':
            text = args[0]
            patterns = args[1].split(',') if len(args) > 1 else None
            result = redact_text(text, patterns=patterns)
            print(result)
        
        elif command == 'conversation':
            conv_id = args[0]
            output = args[1] if len(args) > 1 else None
            patterns = args[2].split(',') if len(args) > 2 else None
            
            redacted = redact_conversation(DB_PATH, conv_id, output, patterns)
            if output:
                print(f"Redacted conversation exported to {output}")
            else:
                print(redacted)
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

