"""파일 쓰기 — 쓰다가 실패해도 원래 있던 파일이 망가지지 않게.

같은 폴더의 임시 파일에 먼저 다 쓴 다음 원래 이름으로 바꿔 놓습니다.
"""
import os
from pathlib import Path


def write_text(path, text, encoding="utf-8", newline="\r\n"):
    """text를 path에 씁니다 (줄 끝은 newline). 실패하면 OSError 또는 UnicodeEncodeError — 원래 파일은 그대로."""
    path = Path(path)
    data = text.replace("\r\n", "\n").replace("\n", newline).encode(encoding)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def why(error):
    """쓰기 실패의 이유를 읽을 수 있는 글로"""
    if isinstance(error, UnicodeEncodeError):
        return f"파일에 적을 수 없는 글자가 있습니다 ('{error.object[error.start:error.end]}')"
    if isinstance(error, PermissionError):
        return "파일을 쓸 수 없습니다 — 다른 프로그램이 그 파일을 열고 있지 않은지 확인하세요"
    return f"파일을 쓸 수 없습니다 ({error})"
