"""설계유속 계산 — 조류 + 취송류와 수심별 분포.

  조류(연직분포):  U_t(z) = U_t0 · ((d + z) / d)^α          (α 기본 1/7, z는 수면 0 · 아래로 음수)
  취송류:          U_w0 = k · U10,   U_w(z) = U_w0 · (1 + z / d0)   (−d0 ≤ z ≤ 0, 그 아래 0)
  설계유속:        U(z) = U_t(z) + U_w(z)   (두 흐름이 같은 방향이라고 봄)

k · d0:  IEC 61400-3-1  k = 0.01, d0 = 20 m
         DNV-RP-C205    k = 0.015 ~ 0.03, d0 = 50 m (수심보다 깊으면 수심까지)
"""
DEFAULT_ALPHA = 1 / 7

WIND_RULES = {
    "IEC 61400-3-1 (k = 0.01, d0 = 20 m)": {"k": 0.01, "d0": 20.0, "ref": "IEC 61400-3-1 취송류 식"},
    "DNV-RP-C205 (k = 0.015, d0 = 50 m)": {"k": 0.015, "d0": 50.0, "ref": "DNV-RP-C205 4.1.4 (k = 0.015~0.03)"},
    "DNV-RP-C205 (k = 0.02, d0 = 50 m)": {"k": 0.02, "d0": 50.0, "ref": "DNV-RP-C205 4.1.4 (k = 0.015~0.03)"},
    "DNV-RP-C205 (k = 0.03, d0 = 50 m)": {"k": 0.03, "d0": 50.0, "ref": "DNV-RP-C205 4.1.4 (k = 0.015~0.03)"},
}
DEFAULT_RULE = next(iter(WIND_RULES))


def wind_surface(k, wind_speed):
    return k * wind_speed


def tidal_at(u0, z, depth, alpha=DEFAULT_ALPHA):
    h = depth + z
    if depth <= 0 or h <= depth * 1e-9:   # 해저면: 부동소수점 오차가 멱법칙에서 작은 값으로 커지지 않게
        return 0.0
    return u0 * (h / depth) ** alpha


def wind_at(u0, z, d0, depth):
    d0 = min(d0, depth)
    if z < -d0:
        return 0.0
    return u0 * (1 + z / d0)


def profile(tidal0, wind0, depth, d0, alpha=DEFAULT_ALPHA, n=12):
    """수면(0)부터 해저(−depth)까지 n+1개 깊이의 [(z, 조류, 취송류, 합계), ...]"""
    rows = []
    for i in range(n + 1):
        z = -depth * i / n
        t, w = tidal_at(tidal0, z, depth, alpha), wind_at(wind0, z, d0, depth)
        rows.append((z, t, w, t + w))
    return rows
