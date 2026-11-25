"""설정 읽기 · 쓰기 — 지금은 공공데이터포털 인증키 하나 (3 수심의 측정점 자동 조회에만 씀, 없어도 됨)."""
import json

import app_paths
import files


def load():
    path = app_paths.settings_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def data_key():
    return str(load().get("data_go_kr_key", "")).strip()


def set_data_key(key):
    data = load()
    data["data_go_kr_key"] = key.strip()
    files.write_text(app_paths.settings_file(), json.dumps(data, ensure_ascii=False, indent=2))
