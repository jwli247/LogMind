import re

SENSITIVE_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd)\s*[:=]\s*([^\s,;]+)",
        ),
        r"\1=[REDACTED_PASSWORD]",
    ),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|secret|access[_-]?token|refresh[_-]?token|token)\s*[:=]\s*([^\s,;]+)",
        ),
        r"\1=[REDACTED_TOKEN]",
    ),
    (
        re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[a-z0-9._~+/=-]+"),
        "Authorization: Bearer [REDACTED_TOKEN]",
    ),
    (
        re.compile(r"\b1[3-9]\d{9}\b"),
        "[REDACTED_PHONE]",
    ),
    (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b",
        ),
        "[REDACTED_IP]",
    ),
)


def sanitize_sensitive_text(text: str) -> str:
    sanitized = text
    for pattern, replacement in SENSITIVE_TEXT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
