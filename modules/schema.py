"""변수 사전 — 프로그램 안에서 값을 주고받을 때는 여기 적힌 이름(key)만 씁니다.

모든 값은 '값 + 출처 + 근거'가 한 묶음(기록)으로 다닙니다 (make_record).
이름 규칙: 영문 소문자 + 밑줄, "분류_항목_재현주기" 순서. 예) deepwave_hs_50yr = 심해설계파 · 유의파고 · 50년
"""
from dataclasses import dataclass
from datetime import datetime

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Field:
    key: str
    name: str
    unit: str
    section: str


_FIELDS = [
    Field("site_lat", "위도", "°N", "1"),
    Field("site_lon", "경도", "°E", "1"),

    # v0.2: 조위 → 수심 차례 (수심 API가 평균해면 기준이라 조위관측소 MSL로 D.L. 환산)
    Field("tide_hat", "최고천문조위 HAT", "m", "2"),
    Field("tide_msl", "평균해수면 MSL", "m", "2"),
    Field("tide_lat", "최저천문조위 LAT", "m", "2"),
    Field("tide_surge_pos", "양(+)의 폭풍해일고", "m", "2"),
    Field("tide_surge_neg", "음(−)의 폭풍해일고", "m", "2"),
    Field("tide_hswl", "설계고조위 HSWL", "m", "2"),
    Field("tide_lswl", "설계저조위 LSWL", "m", "2"),

    Field("water_depth", "수심 (D.L. 기준)", "m", "3"),

    Field("deepwave_hs_50yr", "50년 심해설계파 Hs", "m", "4"),
    Field("deepwave_tp_50yr", "50년 심해설계파 Tp", "s", "4"),
    Field("deepwave_dir_50yr", "50년 심해설계파 방향", "16방위", "4"),
    Field("deepwave_hs_1yr", "1년 심해파 Hs (추정)", "m", "4"),
    Field("deepwave_tp_1yr", "1년 심해파 Tp (추정)", "s", "4"),
    Field("deepwave_table", "재현주기 · 방향별 심해설계파", "m / s", "4"),

    Field("wind_speed_50yr", "50년 해상풍 U10", "m/s", "5"),
    Field("wind_dir_50yr", "50년 해상풍 방향", "16방위", "5"),
    Field("wind_speed_1yr", "1년 해상풍 U10 (추정)", "m/s", "5"),
    Field("wind_table", "재현주기 · 방향별 해상풍", "m/s", "5"),

    Field("current_tidal_max", "최강 조류 (표층)", "m/s", "6"),
    Field("current_tidal_dir", "최강 조류 유향", "°", "6"),
    Field("current_wind_50yr", "50년 취송류 (표층)", "m/s", "6"),
    Field("current_wind_1yr", "1년 취송류 (표층)", "m/s", "6"),
    Field("current_surface_50yr", "50년 설계유속 (표층)", "m/s", "6"),
    Field("current_surface_1yr", "1년 설계유속 (표층)", "m/s", "6"),
    Field("current_shear_exp", "조류 연직분포 지수 α", "-", "6"),
    Field("current_wind_depth", "취송류 소멸 깊이 d0", "m", "6"),
]

FIELDS = {f.key: f for f in _FIELDS}

SECTIONS = {
    "1": "설치위치",
    "2": "설계조위",
    "3": "수심",
    "4": "극한설계파고",
    "5": "설계풍속",
    "6": "설계유속",
}

TABLE_KEYS = {"deepwave_table", "wind_table"}     # 값이 표(dict)인 변수 — 결과 표에는 '(표)'로, HTML에는 따로 표로


def fields_in(section):
    return [f for f in _FIELDS if f.section == section]


def make_record(key, value, source, basis="", ref="", site=None):
    """값 하나를 '값 + 출처 + 근거'가 같이 다니는 기록으로.
    site: 이 값을 어느 좌표 기준으로 구했는지 (lat, lon) — 설치위치가 바뀌면 이 기록은 자동으로 지워집니다."""
    if key not in FIELDS:
        raise KeyError(f"변수 사전에 없는 이름입니다: {key}")
    return {
        "value": value,
        "unit": FIELDS[key].unit,
        "source": source,
        "basis": basis,
        "ref": ref,
        "site": list(site) if site else None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
