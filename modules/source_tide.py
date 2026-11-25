"""2 설계조위 — 항만 및 어항 설계기준(KDS 64 10 10: 2024) 조석 표 (프로그램 안 data/kds_tide_2024.json).

설계조위 = 천문조 + 폭풍해일고:  HSWL = HAT + 양(+)의 해일고,  LSWL = LAT + 음(−)의 해일고
천문조는 가까운 조위관측소의 비조화상수(해설 표 4.4-3)에서 HAT = 약최고고조위(AHHW), LAT = 기본수준면(D.L. = 0.0)으로 둡니다.
해일고는 기준서의 기록 표 3개(4.4-6 · 4.4-7 · 4.4-8)에서 설치위치와 가까운 곳을 후보로 보여 주고 사용자가 고릅니다.
모든 조위는 관측소 기본수준면(D.L.) 기준입니다.
"""
import json

from app_paths import DATA_DIR
from coord import haversine_m

DATA_FILE = DATA_DIR / "kds_tide_2024.json"
STANDARD = "항만 및 어항 설계기준 KDS 64 10 10: 2024"
CANDIDATES_PER_TABLE = 3

_cache = None


def _load():
    global _cache
    if _cache is None:
        _cache = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return _cache


def source():
    return _load()["source"]


def _km(lat, lon, item):
    return haversine_m(lat, lon, item["lat"], item["lon"]) / 1000


def nearest_stations(lat, lon, n=5):
    """[(관측소, 거리 km), ...] — 해설 표 4.4-2 · 4.4-3의 45개 조위관측소."""
    return sorted(((s, _km(lat, lon, s)) for s in _load()["stations"]), key=lambda t: t[1])[:n]


def get_station(name):
    return next((s for s in _load()["stations"] if s["name"] == name), None)


def extreme_of(station_name):
    """그 관측소의 최극조위 기록(해설 표 4.4-8). 없으면 None."""
    return next((e for e in _load()["extremes"] if e["station"] == station_name), None)


def astro_levels(station):
    nh = station["nonharmonic"]
    return {"hat": nh["ahhw"], "hwost": nh["hwost"], "msl": nh["msl"], "lat": 0.0,
            "spr": nh["spr"], "npr": nh["npr"], "form": nh["form"]}


def surge_candidates(lat, lon):
    """기준서 표 3개에서 각각 설치위치와 가까운 해일고 후보 — 전체를 가까운 순으로.
    각 후보: id, table, place, km, pos(+, m), neg(−, m 또는 None), period, note, ref"""
    src = source()
    out = []

    ranked = sorted(((e, _km(lat, lon, e)) for e in _load()["surge_1959_1981"]), key=lambda t: t[1])
    for e, km in ranked[:CANDIDATES_PER_TABLE]:
        out.append({
            "id": f"t446:{e['port']}", "table": "표 4.4-6 최대 조위편차", "place": e["port"], "km": km,
            "pos": e["pos"], "neg": e["neg"], "period": "1959~1981",
            "note": f"고조 {e['pos_date']} {e['pos_cause']} / 저조 {e['neg_date']} {e['neg_cause']}",
            "ref": src["surge_1959_1981"],
        })

    usable = [e for e in _load()["extremes"] if e["station"]]
    ranked = sorted(((e, _km(lat, lon, e)) for e in usable), key=lambda t: t[1])
    for e, km in ranked[:CANDIDATES_PER_TABLE]:
        ahhw = get_station(e["station"])["nonharmonic"]["ahhw"]
        out.append({
            "id": f"t448:{e['name']}", "table": "표 4.4-8 최극조위 − 천문조", "place": e["name"], "km": km,
            "pos": round(e["hhw"] - ahhw, 3), "neg": e["llw"], "period": f"{e['period']} ({e['years']}년)",
            "note": (f"고극조위 {e['hhw']} ({e['hhw_date']}) − 약최고고조위 {ahhw} / "
                     f"저극조위 {e['llw']} ({e['llw_date']}) − 기본수준면 0.0"),
            "ref": f"{src['extremes']}, {src['nonharmonic']}",
        })

    best = {}
    for e in _load()["surge_2012"]:
        if e["place"] not in best or e["surge"] > best[e["place"]]["surge"]:
            best[e["place"]] = e
    ranked = sorted(((e, _km(lat, lon, e)) for e in best.values()), key=lambda t: t[1])
    for e, km in ranked[:CANDIDATES_PER_TABLE]:
        out.append({
            "id": f"t447:{e['place']}", "table": "표 4.4-7 2012 태풍 해일", "place": e["place"], "km": km,
            "pos": e["surge"], "neg": None, "period": "2012",
            "note": f"{e['typhoon']} ({e['period']}) 최대 해일고, 저조 쪽 기록 없음",
            "ref": src["surge_2012"],
        })
    return sorted(out, key=lambda c: c["km"])


def design_levels(astro, pos, neg):
    """HSWL = HAT + pos,  LSWL = LAT + neg (neg는 음수)."""
    return {"hswl": round(astro["hat"] + pos, 3),
            "lswl": round(astro["lat"] + neg, 3) if neg is not None else None}
