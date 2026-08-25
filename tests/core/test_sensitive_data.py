from core.sensitive_data import sanitize_sensitive_text


def test_sanitize_sensitive_text_redacts_common_secrets() -> None:
    text = (
        "password=abc123 token: sk-test-123 Authorization: Bearer abc.def "
        "phone=13800138000 host=192.168.1.10"
    )

    sanitized = sanitize_sensitive_text(text)

    assert "abc123" not in sanitized
    assert "sk-test-123" not in sanitized
    assert "abc.def" not in sanitized
    assert "13800138000" not in sanitized
    assert "192.168.1.10" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_IP]" in sanitized


def test_sanitize_sensitive_text_keeps_non_sensitive_text() -> None:
    text = "Spring Boot failed to start because port 8080 is already in use."

    assert sanitize_sensitive_text(text) == text
