"""프로그램이 쓰는 폴더 위치.

APP_DIR  : 프로그램 파일과 함께 배포되는 자료(data · web)가 있는 곳 — exe로 묶었을 때는 그 안의 폴더
USER_DIR : 사용하는 사람의 컴퓨터에만 남는 것(인증키 설정 · 지도 창 기록 · 오류 기록) — 프로그램 폴더 밖에 두어서
           프로그램 폴더를 그대로 복사해 나눠 줘도 인증키가 딸려 가지 않게 합니다.
           (환경변수 KOMPAS_HOME이 있으면 그 폴더를 씀 — 시험용)
"""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(getattr(sys, "_MEIPASS", "")) if FROZEN else Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
WEB_DIR = APP_DIR / "web"


def user_dir():
    base = os.environ.get("KOMPAS_HOME") or os.path.join(os.environ.get("LOCALAPPDATA") or str(Path.home()), "KOMPAS")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file():
    return user_dir() / "settings.json"


def error_log():
    return user_dir() / "오류 기록.txt"


def map_profile_dir():
    return user_dir() / "map_profile"
