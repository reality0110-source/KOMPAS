"""좌표 형식 변환 — 십진법(DD) / 도분초(DMS) / 도분(DM) / UTM ↔ 위경도(십진법, WGS84).

프로그램 안에서는 좌표를 항상 십진법 위경도(site_lat, site_lon)로만 저장하고, 다른 형식은 입력 · 표시할 때만 바꿉니다.
우리나라 주변(북위 · 동경)만 가정합니다. UTM은 WGS84 Snyder 공식.
"""
import math

_A = 6378137.0
_F = 1 / 298.257223563
_K0 = 0.9996

KOREA_BOUNDS = (32.0, 39.5, 123.0, 132.5)


def in_korea_waters(lat, lon):
    lat_min, lat_max, lon_min, lon_max = KOREA_BOUNDS
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def dms_to_dd(deg, minute, sec):
    return abs(deg) + abs(minute) / 60 + abs(sec) / 3600


def dm_to_dd(deg, minute):
    return abs(deg) + abs(minute) / 60


def dd_to_dms(dd):
    deg = int(dd)
    minutes_full = (dd - deg) * 60
    minute = int(minutes_full)
    sec = round((minutes_full - minute) * 60, 2)
    if sec >= 60:
        sec, minute = 0.0, minute + 1
    if minute >= 60:
        minute, deg = 0, deg + 1
    return deg, minute, sec


def dd_to_dm(dd):
    deg = int(dd)
    return deg, (dd - deg) * 60


def dd_to_utm(lat, lon, zone=None):
    """위경도(십진법) → (zone, hemi, easting, northing).
    zone을 주면 그 구역 기준으로 계산 (동경 126° 서쪽 지점도 52N으로 쓰는 자료가 있어 입력한 구역 그대로 보여 주려는 용도)."""
    a, f, k0 = _A, _F, _K0
    b = a * (1 - f)
    e2 = (a * a - b * b) / (a * a)
    ep2 = (a * a - b * b) / (b * b)

    if zone is None:
        zone = math.floor((lon + 180) / 6) + 1
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)

    N = a / math.sqrt(1 - e2 * math.sin(lat_r) ** 2)
    T = math.tan(lat_r) ** 2
    C = ep2 * math.cos(lat_r) ** 2
    A = math.cos(lat_r) * (lon_r - lon0)

    M = a * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat_r
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * lat_r)
        + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * lat_r)
        - (35 * e2 ** 3 / 3072) * math.sin(6 * lat_r)
    )

    E = k0 * N * (A + (1 - T + C) * A ** 3 / 6
                  + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000
    Nn = k0 * (M + N * math.tan(lat_r) * (
        A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
        + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720))
    if lat < 0:
        Nn += 10000000

    return zone, ("N" if lat >= 0 else "S"), round(E), round(Nn)


def utm_to_dd(zone, hemi, easting, northing):
    """UTM → 위경도(십진법)."""
    a, f, k0 = _A, _F, _K0
    e2 = f * (2 - f)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    ep2 = e2 / (1 - e2)

    x = easting - 500000.0
    y = float(northing)
    if hemi.upper() == "S":
        y -= 10000000.0

    M = y / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))

    phi1 = (mu
            + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))

    N1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = ep2 * math.cos(phi1) ** 2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D ** 2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720
    )
    lon = (D - (1 + 2 * T1 + C1) * D ** 3 / 6
           + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120
           ) / math.cos(phi1)

    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    return math.degrees(lat), math.degrees(lon0 + lon)


def parse_utm_zone(zone_text):
    """'52N' → (52, 'N'). 반구를 생략하면 N."""
    s = str(zone_text).strip().upper()
    if s and s[-1] in ("N", "S"):
        return int(s[:-1]), s[-1]
    return int(s), "N"


UTM_SOURCE = "좌표 입력 (UTM)"


def entered_utm_zone(source, basis):
    """UTM으로 입력해 정한 설치위치면 그때 고른 구역 번호(예: 52), 아니면 None.
    기록에는 source '좌표 입력 (UTM)', basis '입력값: 52N / 173990.4 / 3806729.3' 로 남음."""
    if source != UTM_SOURCE or not basis or not str(basis).startswith("입력값:"):
        return None
    try:
        return parse_utm_zone(str(basis)[len("입력값:"):].split("/")[0])[0]
    except (ValueError, IndexError):
        return None


def utm_note(lat, lon, utm_zone):
    """보여 주는 UTM 구역이 정식 구역(경도로 정한 구역)과 다를 때 안내 글 — 같거나 구역을 모르면 빈 글."""
    if utm_zone is None:
        return ""
    nat, hemi, e, n = dd_to_utm(lat, lon)
    if nat == utm_zone:
        return ""
    lo = (nat - 1) * 6 - 180
    return (f"※ 입력한 {utm_zone}{hemi} 기준으로 표시했습니다. 이 지점의 정식 구역은 {nat}{hemi}(동경 {lo}~{lo + 6}°)이고, "
            f"그 구역으로는 E {e:,}  N {n:,} 입니다 (같은 지점).")


def format_all(lat, lon, utm_zone=None):
    """같은 좌표를 네 가지 형식 글로. utm_zone을 주면 UTM을 그 구역으로 표시."""
    la_d, la_m, la_s = dd_to_dms(lat)
    lo_d, lo_m, lo_s = dd_to_dms(lon)
    la_dm_d, la_dm_m = dd_to_dm(lat)
    lo_dm_d, lo_dm_m = dd_to_dm(lon)
    zone, hemi, e, n = dd_to_utm(lat, lon, utm_zone)
    return {
        "DD": f"{lat:.6f}°N, {lon:.6f}°E",
        "DMS": f"{la_d}° {la_m:02d}' {la_s:05.2f}\" N,  {lo_d}° {lo_m:02d}' {lo_s:05.2f}\" E",
        "DM": f"{la_dm_d}° {la_dm_m:07.4f}' N,  {lo_dm_d}° {lo_dm_m:07.4f}' E",
        "UTM": f"{zone}{hemi}  E {e:,}  N {n:,}",
    }


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
