"""4 극한설계파고 · 5 설계풍속 — 해양수산부(2019) 재현주기별 심해설계파 · 해상풍 격자자료 (프로그램 안 data/grid_points.json).

전국 520개 격자점, 재현주기 10 · 20 · 30 · 50 · 100년, 16방위. 원본 엑셀 2개의 값을 그대로 옮긴 파일입니다.
1년 값은 원본에 없어서 10~100년 값으로 회귀 외삽한 추정치입니다 (값 = a + b·ln(T)에 T = 1).
"""
import json
import math

from app_paths import DATA_DIR
from coord import haversine_m

DATA_FILE = DATA_DIR / "grid_points.json"
SOURCE_NAME = "해양수산부 (2019) 빈도별 심해설계파 · 해상풍 제원 — 전국 520개 격자점"
ONE_YR_BASIS = "1년 값은 원본에 없어 10~100년 값을 ln(T) 회귀로 외삽한 추정치"

_cache = None


def _load():
    global _cache
    if _cache is None:
        _cache = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return _cache


def directions():
    return _load()["directions"]


def return_periods():
    return _load()["return_periods"]


def source_files():
    src = _load()["source"]
    return f'{src["wave_file"]}, {src["wind_file"]}'


def nearest_points(lat, lon, n=5):
    """[(격자점, 거리 km), ...] 가까운 순."""
    ranked = sorted(((p, haversine_m(lat, lon, p["lat"], p["lon"]) / 1000) for p in _load()["points"]),
                    key=lambda t: t[1])
    return ranked[:n]


def _loglinear_at_1yr(rps, ys):
    lnx = [math.log(x) for x in rps]
    mx, my = sum(lnx) / len(lnx), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(lnx, ys)) / sum((x - mx) ** 2 for x in lnx)
    return my - b * mx


def _linear_fit(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return my - b * mx, b


def _estimate_1yr(point, getter):
    """방향별 1년 추정치. 외삽 결과가 0 이하면 None."""
    rps = return_periods()
    out = {}
    for d in directions():
        v = _loglinear_at_1yr(rps, [getter(point, rp, d) for rp in rps])
        out[d] = round(v, 2) if v > 0 else None
    return out


def hs_1yr(point):
    return _estimate_1yr(point, lambda p, rp, d: p["wave"][str(rp)]["hs"][d])


def wind_1yr(point):
    return _estimate_1yr(point, lambda p, rp, d: p["wind"][str(rp)]["speed"][d])


def tp_1yr(point, hs1):
    """Tp는 그 방향의 Hs-Tp 관계(10~100년 5쌍)를 직선회귀한 뒤 1년 Hs를 대입."""
    rps = return_periods()
    out = {}
    for d in directions():
        h1 = hs1.get(d)
        if h1 is None:
            out[d] = None
            continue
        c, slope = _linear_fit([point["wave"][str(rp)]["hs"][d] for rp in rps],
                               [point["wave"][str(rp)]["tp"][d] for rp in rps])
        v = c + slope * h1
        out[d] = round(v, 2) if v > 0 else None
    return out


def governing(values_by_dir):
    """방향별 값 중 최댓값 → (방향, 값). None은 건너뜀."""
    valid = [(d, v) for d, v in values_by_dir.items() if d in directions() and v is not None]
    return max(valid, key=lambda t: t[1]) if valid else (None, None)


def wave_summary(point):
    dirs = directions()
    dir50, h50 = governing({d: point["wave"]["50"]["hs"][d] for d in dirs})
    hs1 = hs_1yr(point)
    tp1 = tp_1yr(point, hs1)
    dir1, h1 = governing(hs1)
    table = {
        "hs": {rp: {d: point["wave"][rp]["hs"][d] for d in dirs} for rp in point["wave"]},
        "tp": {rp: {d: point["wave"][rp]["tp"][d] for d in dirs} for rp in point["wave"]},
        "cause": {rp: {d: point["wave"][rp]["cause"][d] for d in dirs} for rp in point["wave"]},
        "hs_1yr_est": hs1,
        "tp_1yr_est": tp1,
    }
    return {"hs_50yr": h50, "tp_50yr": point["wave"]["50"]["tp"][dir50] if dir50 else None, "dir_50yr": dir50,
            "hs_1yr": h1, "tp_1yr": tp1.get(dir1) if dir1 else None, "dir_1yr": dir1, "table": table}


def wind_summary(point):
    dirs = directions()
    dir50, v50 = governing({d: point["wind"]["50"]["speed"][d] for d in dirs})
    u1 = wind_1yr(point)
    dir1, v1 = governing(u1)
    table = {"speed": {rp: {d: point["wind"][rp]["speed"][d] for d in dirs} for rp in point["wind"]},
             "speed_1yr_est": u1}
    return {"u_50yr": v50, "dir_50yr": dir50, "u_1yr": v1, "dir_1yr": dir1, "table": table}
