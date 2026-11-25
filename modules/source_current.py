"""6 설계유속 — 국립해양조사원 조류예보(최강창낙조) 자료를 예보지점마다 미리 받아 정리해 둔 파일(data/tidal_current.json).

프로그램은 이 파일만 읽으므로 인증키 없이 씁니다. 파일은 tools/update_current.py로 다시 만듭니다
(지점마다 받은 날짜 · 예보 기간이 함께 적혀 있음).
"""
import json
import math

from app_paths import DATA_DIR
from coord import haversine_m

DATA_FILE = DATA_DIR / "tidal_current.json"
SOURCE_NAME = "국립해양조사원 조류예보 최강창낙조 및 전류 (공공데이터포털 API)"
BASE_URL = "https://apis.data.go.kr/1192136/crntFcstFldEbb/GetCrntFcstFldEbbApiService"

_cache = None


def _load():
    global _cache
    if _cache is None:
        _cache = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"stations": []}
    return _cache


def stations():
    return _load()["stations"]


def nearest_stations(lat, lon, n=6):
    """[(지점, 거리 km), ...] — 자료가 있는 지점만"""
    return sorted(((s, haversine_m(lat, lon, s["lat"], s["lon"]) / 1000) for s in stations()),
                  key=lambda t: t[1])[:n]


def source_text(st):
    """출처 한 줄 — 기관 · 자료명 · 지점 · 받은 날 · 예보 기간"""
    return (f"{SOURCE_NAME}, 지점 {st['name']}({st['code']}), {st['fetched']} 받음, "
            f"예보 기간 {st['from'][:10]} ~ {st['to'][:10]}")


# ── 받은 자료 정리 (tools/update_current.py가 씀) ──

def _ang_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _mean_dir(dirs):
    x = sum(math.cos(math.radians(d)) for d in dirs)
    y = sum(math.sin(math.radians(d)) for d in dirs)
    return math.degrees(math.atan2(y, x)) % 360


def analyze(items):
    """최강류 기록들을 흐름 방향 두 무리로 나눠 무리별 최대 · 평균을 구합니다.
    (어느 쪽이 창조(밀물)인지는 자료에 없어서 방향으로만 구분)"""
    flows = [(it["predcDt"], float(it["crsp"]) / 100, float(it["crdir"])) for it in items if float(it["crsp"]) > 0]
    if not flows:
        return None
    top = max(flows, key=lambda f: f[1])
    groups = {"A": [], "B": []}
    for f in flows:
        groups["A" if _ang_diff(f[2], top[2]) <= 90 else "B"].append(f)
    out = {"count": len(flows), "from": items[0]["predcDt"], "to": items[-1]["predcDt"], "groups": {}}
    for g, fs in groups.items():
        if not fs:
            continue
        mx = max(fs, key=lambda f: f[1])
        out["groups"][g] = {"n": len(fs), "max": round(mx[1], 3), "max_dir": round(mx[2], 1), "max_time": mx[0],
                            "mean": round(sum(f[1] for f in fs) / len(fs), 3),
                            "mean_dir": round(_mean_dir([f[2] for f in fs]), 1)}
    out["max"], out["max_dir"], out["max_time"] = round(top[1], 3), round(top[2], 1), top[0]
    return out
