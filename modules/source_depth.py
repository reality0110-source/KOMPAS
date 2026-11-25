"""3 수심 — 국립해양조사원 자연과학용 수심정보 API (공공데이터포털 인증키 필요).

API는 사각형 범위 안의 측정점을 위도 순으로 한 번에 최대 300개씩(페이지) 돌려줍니다. 범위를 넓게 잡고 첫 페이지만
받으면 범위의 남쪽 가장자리 점들만 받게 되므로, 설치위치 바로 주변의 작은 범위를 잡고 모든 페이지를 받습니다.

기준면 (v0.2): 이 API의 수심은 평균해면(MSL) 기준입니다. 응답 · 활용가이드에는 적혀 있지 않아서, 기본수준면(D.L.) 기준
수심측량 보고서 4곳(인천 덕적 · 여수 연도 1 · 2단계 · 통영 욕지도)과 같은 지점을 견줘 확인했습니다
(API − 측량 = +3.71 · +1.35 · +1.96 · +1.41 m ≈ 그 지역 조위관측소 평균해면 높이 3.87 · 1.8 · 1.8 · 1.41 m).
설계조위(HAT · HSWL 등)는 D.L. 기준이므로, 수심도 조위관측소 평균해면 높이를 빼서 D.L. 기준으로 바꿔 씁니다.
v0.1은 빼지 않아 수심이 평균해면 높이만큼 깊게 나왔습니다(서해 3 ~ 4.6 m, 남해 1 ~ 2.4 m, 동해 0.1 ~ 0.3 m).
API 값의 부호도 그대로 둡니다(음수 = 평균해면 위로 드러나는 곳 — v0.1은 절댓값으로 바꿨음).
"""
from dataclasses import dataclass, field

import net
import source_tide as kt
from coord import haversine_m

BASE_URL = "http://apis.data.go.kr/1192136/waterDepth/GetWaterDepthApiService"
SOURCE_NAME = "국립해양조사원 자연과학용 수심정보 (공공데이터포털 API)"
API_GUIDE = "공공데이터포털(data.go.kr)에서 '국립해양조사원_자연과학용 수심정보' 활용신청 후 받은 인증키"
DATUM_NOTE = ("이 API의 수심은 평균해면(MSL) 기준이라, 조위관측소 평균해면 높이를 빼서 D.L.(기본수준면) 기준으로 바꿉니다 "
              "(D.L. 기준 수심측량 보고서 4곳과 견줘 확인).")

PAGE_SIZE = 300
MAX_POINTS = 3000
START_HALF_DEG = 0.01
MAX_HALF_DEG = 0.08
MIN_POINTS = 5

METHODS = {
    "idw5": "최근접 5개 역거리가중평균",
    "nearest": "최근접 측정점",
    "idw_all": "조회범위 전체 역거리가중평균",
}
DEFAULT_METHOD = "idw5"


class DepthError(Exception):
    pass


@dataclass
class DepthResult:
    lat: float
    lon: float
    half_deg: float
    total: int
    ranked: list                 # [(거리 m, (위도, 경도, API 수심 — 평균해면 기준))]
    methods_msl: dict            # 방법별 API 수심 (평균해면 기준)
    msl: float                   # 뺀 평균해면 높이 (D.L. 위, m)
    msl_note: str                # 어느 조위관측소 값인지
    methods: dict = field(default_factory=dict)   # 방법별 D.L. 기준 수심 = API − MSL

    def __post_init__(self):
        self.methods = {k: v - self.msl for k, v in self.methods_msl.items()}

    def basis(self, method):
        return (f"설치위치 ±{self.half_deg:g}° 범위 측정점 {len(self.ranked)}개 중 {METHODS[method]}, "
                f"최근접 측정점 거리 {self.ranked[0][0]:.0f} m. "
                f"API 수심(평균해면 기준) {self.methods_msl[method]:.2f} m − MSL {self.msl:.3f} m ({self.msl_note}) "
                f"= D.L. 기준 {self.methods[method]:.2f} m")


def default_msl(lat, lon):
    """설치위치에서 가장 가까운 조위관측소의 평균해면 높이 (2 설계조위 탭의 기본 관측소와 같음)."""
    st, km = kt.nearest_stations(lat, lon, n=1)[0]
    return st["nonharmonic"]["msl"], f"조위관측소 {st['name']} {km:.1f} km, 해설 표 4.4-3"


def _request(key, lat, lon, half, page):
    params = {"serviceKey": key, "type": "json",
              "ymin": f"{lat - half:.4f}", "ymax": f"{lat + half:.4f}",
              "xmin": f"{lon - half:.4f}", "xmax": f"{lon + half:.4f}",
              "numOfRows": PAGE_SIZE, "pageNo": page}
    try:
        body = net.get_json(BASE_URL, params)
    except net.ApiError as e:
        raise DepthError(str(e)) from e
    points = [(float(it["lat"]), float(it["lot"]), float(it["dpwt"])) for it in net.items_of(body)]   # 부호 그대로
    return points, int(body.get("totalCount", 0))


def _fetch_box(key, lat, lon, half):
    points, total = _request(key, lat, lon, half, 1)
    if total > MAX_POINTS:
        return None, total
    page = 1
    while page * PAGE_SIZE < total:
        page += 1
        more, _ = _request(key, lat, lon, half, page)
        points.extend(more)
    return points, total


def _idw(ranked):
    for dist, (_, _, depth) in ranked:
        if dist < 1.0:
            return depth
    weights = [1 / d ** 2 for d, _ in ranked]
    return sum(w * p[2] for w, (_, p) in zip(weights, ranked)) / sum(weights)


def estimate(key, lat, lon, msl=None, msl_note=None):
    """설치위치 수심. msl을 주면 그 값(2 설계조위에서 반영한 MSL)을, 안 주면 가장 가까운 조위관측소 값을 뺌."""
    if not key:
        raise DepthError("인증키가 없습니다.")
    if msl is None:
        msl, msl_note = default_msl(lat, lon)
    half = START_HALF_DEG
    while True:
        points, total = _fetch_box(key, lat, lon, half)
        if points is None:
            half /= 2
            continue
        if len(points) >= MIN_POINTS or half >= MAX_HALF_DEG:
            break
        half *= 2
    if not points:
        raise DepthError(f"설치위치 ±{half:g}° 범위에 수심 측정점이 없습니다.")
    ranked = sorted(((haversine_m(lat, lon, p[0], p[1]), p) for p in points), key=lambda t: t[0])
    methods_msl = {"nearest": ranked[0][1][2], "idw5": _idw(ranked[:5]), "idw_all": _idw(ranked)}
    return DepthResult(lat, lon, half, total, ranked, methods_msl, msl, msl_note or "")
