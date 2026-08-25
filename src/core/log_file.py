from pathlib import Path

from core.sensitive_data import sanitize_sensitive_text
from schema import LogFilePreview

ALLOWED_LOG_FILE_EXTENSIONS = {".log", ".txt"}
MAX_LOG_FILE_BYTES = 1024 * 1024
MAX_LOG_CONTENT_CHARS = 12000


class LogFileValidationError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def prepare_log_file_preview(
    *,
    filename: str,
    content_bytes: bytes,
    max_bytes: int = MAX_LOG_FILE_BYTES,
    max_chars: int = MAX_LOG_CONTENT_CHARS,
) -> LogFilePreview:
    if not filename:
        raise LogFileValidationError("Missing filename")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_LOG_FILE_EXTENSIONS:
        raise LogFileValidationError("Only .log and .txt files are supported")

    size_bytes = len(content_bytes)
    if size_bytes == 0:
        raise LogFileValidationError("Uploaded log file is empty")

    if size_bytes > max_bytes:
        raise LogFileValidationError("Uploaded log file is too large", status_code=413)

    content = _decode_log_content(content_bytes)
    content = content.replace("\x00", "")
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]

    sanitized_content = sanitize_sensitive_text(content).strip()
    diagnostic_message = (
        f"请分析以下日志文件并给出故障诊断、关键证据、可能原因、排查步骤和修复建议。\n\n"
        f"文件名：{filename}\n"
        f"文件大小：{size_bytes} bytes\n"
        f"内容是否截断：{'是' if truncated else '否'}\n\n"
        f"日志内容：\n{sanitized_content}"
    )

    return LogFilePreview(
        filename=filename,
        size_bytes=size_bytes,
        truncated=truncated,
        content=sanitized_content,
        diagnostic_message=diagnostic_message,
    )


def _decode_log_content(content_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "latin-1"):
        try:
            return content_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return content_bytes.decode("utf-8", errors="replace")
