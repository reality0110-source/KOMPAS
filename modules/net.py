"""공공데이터포털 API 호출 — 파이썬 기본 기능(urllib)만 씀. 연결이 잠깐 끊기면 몇 번 다시 시도합니다."""
import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request

RETRIES = 3


class ApiError(Exception):
    pass


def get_json(url, params, timeout=30):
    """data.go.kr 형식 응답 → (body dict). 오류면 ApiError (resultCode가 있으면 메시지에 포함)."""
    full = f"{url}?{urllib.parse.urlencode(params)}"
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(full, timeout=timeout) as res:
                raw = res.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):        # 다시 해도 같음 — 바로 알림
                raise ApiError(f"서버가 요청을 거절했습니다 ({e.code}) — 인증키와 그 API의 활용신청 승인을 확인하세요") from None
            last = f"서버 응답 {e.code}"
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as e:
            last = f"연결 실패 ({e})"
        time.sleep(1.0 + attempt)
    else:
        raise ApiError(last)
    text = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError:
        raise ApiError(f"응답을 읽을 수 없습니다 — 인증키를 확인하세요 ({text[:160]})") from None
    header = data.get("header") or data.get("response", {}).get("header", {})
    code = str(header.get("resultCode", ""))
    if code not in ("00", "0"):
        raise ApiError(f"API 오류 [{code}] {header.get('resultMsg', '')}")
    return data.get("body") or data.get("response", {}).get("body", {})


def items_of(body):
    items = body.get("items")
    items = items.get("item", []) if isinstance(items, dict) else (items or [])
    return [items] if isinstance(items, dict) else items
