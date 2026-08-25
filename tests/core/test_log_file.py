import pytest

from core.log_file import LogFileValidationError, prepare_log_file_preview


def test_prepare_log_file_preview_returns_diagnostic_message() -> None:
    preview = prepare_log_file_preview(
        filename="app.log",
        content_bytes=b"ERROR password=abc123 token=secret port 8080 failed",
    )

    assert preview.filename == "app.log"
    assert preview.size_bytes > 0
    assert preview.truncated is False
    assert "abc123" not in preview.content
    assert "secret" not in preview.content
    assert "[REDACTED_PASSWORD]" in preview.content
    assert "[REDACTED_TOKEN]" in preview.content
    assert "文件名：app.log" in preview.diagnostic_message
    assert "日志内容：" in preview.diagnostic_message


def test_prepare_log_file_preview_rejects_unsupported_extension() -> None:
    with pytest.raises(LogFileValidationError) as exc_info:
        prepare_log_file_preview(
            filename="app.json",
            content_bytes=b'{"error": "failed"}',
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Only .log and .txt files are supported"


def test_prepare_log_file_preview_rejects_empty_file() -> None:
    with pytest.raises(LogFileValidationError) as exc_info:
        prepare_log_file_preview(filename="app.log", content_bytes=b"")

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Uploaded log file is empty"


def test_prepare_log_file_preview_rejects_large_file() -> None:
    with pytest.raises(LogFileValidationError) as exc_info:
        prepare_log_file_preview(
            filename="app.log",
            content_bytes=b"x" * 11,
            max_bytes=10,
        )

    assert exc_info.value.status_code == 413
    assert str(exc_info.value) == "Uploaded log file is too large"


def test_prepare_log_file_preview_truncates_long_content() -> None:
    preview = prepare_log_file_preview(
        filename="app.txt",
        content_bytes=b"abcdef",
        max_chars=3,
    )

    assert preview.truncated is True
    assert preview.content == "abc"
    assert "内容是否截断：是" in preview.diagnostic_message
