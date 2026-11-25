"""조류 자료 갱신 — 국립해양조사원 조류예보(최강창낙조) 예보지점을 모두 받아 data/tidal_current.json을 다시 만듭니다.

  창으로:   이 파일을 더블클릭(또는 python update_current.py) → 인증키를 넣고 [시작]
  명령줄:   python update_current.py --cli          (인증키는 환경변수 KOMPAS_KEY)
            --max-age-days 30   이 날수보다 최근에 받은 지점은 다시 받지 않음 (0이면 모두 다시)
            --build-only        받지 않고, 받아 둔 자료로 파일만 다시 만듦

받은 지점 원자료는 tools/cache/에 남깁니다(배포에는 넣지 않음). 인증키는 어디에도 저장하지 않습니다.
지점 목록은 tools/current_stations.json (국립해양조사원 오픈API 활용가이드의 예보지점 목록).
"""
import argparse
import json
import math
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR.parent / "modules"))

import files  # noqa: E402
import net  # noqa: E402
import source_current as sc  # noqa: E402

STATIONS_FILE = TOOLS_DIR / "current_stations.json"
CACHE_DIR = TOOLS_DIR / "cache"
PAGE_SIZE = 300
PAUSE_SEC = 0.05
QUOTA_CODE = "[22]"          # 하루 호출 한도를 넘음 — 멈추고 받은 만큼으로 파일을 만듦


class QuotaExceeded(Exception):
    pass


def station_list():
    return json.loads(STATIONS_FILE.read_text(encoding="utf-8"))["stations"]


def _cache_path(code):
    return CACHE_DIR / f"crnt_{code}.json"


def _cached(code):
    p = _cache_path(code)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _page(key, code, page):
    params = {"serviceKey": key, "type": "json", "obsCode": code, "numOfRows": PAGE_SIZE, "pageNo": page}
    try:
        body = net.get_json(sc.BASE_URL, params, timeout=60)
    except net.ApiError as e:
        if QUOTA_CODE in str(e):
            raise QuotaExceeded(str(e)) from e
        raise
    return net.items_of(body), int(body.get("totalCount", 0))


def fetch_station(key, code):
    items, total = _page(key, code, 1)
    for p in range(2, math.ceil(total / PAGE_SIZE) + 1):
        time.sleep(PAUSE_SEC)
        more, _ = _page(key, code, p)
        items.extend(more)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"code": code, "fetched_at": datetime.now().isoformat(timespec="seconds"), "items": items}
    files.write_text(_cache_path(code), json.dumps(data, ensure_ascii=False), newline="\n")
    return len(items)


def build():
    """받아 둔 원자료로 data/tidal_current.json을 만듦 → (넣은 지점 수, 자료 없는 지점 목록)"""
    out, missing = [], []
    for st in station_list():
        c = _cached(st["code"])
        a = sc.analyze(c["items"]) if c and c.get("items") else None
        if not a:
            missing.append(st["code"])
            continue
        out.append({"code": st["code"], "name": st["name"], "lat": st["lat"], "lon": st["lon"],
                    "fetched": c["fetched_at"][:10], **a})
    data = {"source": {"name": sc.SOURCE_NAME, "api": sc.BASE_URL,
                       "stations": "국립해양조사원 오픈API 활용가이드 — 조류예보 최강창낙조 및 전류, 예보지점 목록"},
            "built": datetime.now().date().isoformat(), "stations": out}
    files.write_text(sc.DATA_FILE, json.dumps(data, ensure_ascii=False, indent=1), newline="\n")
    return len(out), missing


def run(key, max_age_days=30, log=print):
    """모든 지점을 (오래된 것만) 받고 파일을 만듦. 하루 한도에 걸리면 거기서 멈추고 받은 만큼으로 만듦.
    max_age_days가 None이면 받아 둔 지점은 날짜와 상관없이 두고, 없는 지점만 받음."""
    stations = station_list()
    todo = []
    for st in stations:
        c = _cached(st["code"])
        if c and (max_age_days is None or (max_age_days > 0 and
                                           datetime.fromisoformat(c["fetched_at"]) >= datetime.now() - timedelta(days=max_age_days))):
            continue
        todo.append(st)
    log(f"지점 {len(stations)}곳 중 새로 받을 곳 {len(todo)}곳")
    for i, st in enumerate(todo, 1):
        try:
            n = fetch_station(key, st["code"])
            log(f"[{i}/{len(todo)}] {st['name']} ({st['code']}) — {n}건")
        except QuotaExceeded as e:
            log(f"하루 호출 한도에 걸려 멈춥니다 ({e}) — 내일 다시 [시작]하면 남은 곳만 받습니다.")
            break
        except net.ApiError as e:
            log(f"[{i}/{len(todo)}] {st['name']} ({st['code']}) — 받지 못함: {e}")
    n, missing = build()
    log(f"완료 — {sc.DATA_FILE.name}에 {n}곳을 넣었습니다." + (f" 자료 없는 곳 {len(missing)}곳: {', '.join(missing)}"
                                                                if missing else ""))


def _gui():
    import queue
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("KOMPAS — 조류 자료 갱신")
    root.geometry("720x480")
    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="공공데이터포털 인증키 ('국립해양조사원_조류예보 최강창낙조 및 전류' 활용신청) — 저장하지 않습니다").pack(anchor="w")
    key_var = tk.StringVar(value=os.environ.get("KOMPAS_KEY", ""))
    ttk.Entry(frm, textvariable=key_var, show="•").pack(fill="x", pady=(2, 8))
    row = ttk.Frame(frm)
    row.pack(fill="x")
    ttk.Label(row, text="이 날수보다 최근에 받은 지점은 건너뜀").pack(side="left")
    age_var = tk.StringVar(value="30")
    ttk.Entry(row, textvariable=age_var, width=6).pack(side="left", padx=6)
    btn = ttk.Button(row, text="시작")
    btn.pack(side="right")
    box = tk.Text(frm, height=20)
    box.pack(fill="both", expand=True, pady=(8, 0))
    q = queue.Queue()

    def pump():
        while not q.empty():
            msg = q.get()
            if msg is None:
                btn.configure(state="normal")
            else:
                box.insert("end", msg + "\n")
                box.see("end")
        root.after(200, pump)

    def start():
        key = key_var.get().strip()
        if not key:
            box.insert("end", "인증키를 넣어 주세요.\n")
            return
        try:
            age = int(age_var.get())
        except ValueError:
            age = 30
        btn.configure(state="disabled")

        def work():
            try:
                run(key, age, log=q.put)
            except Exception as e:      # 창에 이유를 보여 주고 끝냄
                q.put(f"오류: {e}")
            q.put(None)
        threading.Thread(target=work, daemon=True).start()

    btn.configure(command=start)
    pump()
    root.mainloop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--max-age-days", type=int, default=30)
    ap.add_argument("--missing-only", action="store_true", help="받아 둔 지점은 그대로, 없는 지점만 받음")
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()
    if args.build_only:
        print(build())
    elif args.cli:
        k = os.environ.get("KOMPAS_KEY", "").strip()
        if not k:
            sys.exit("환경변수 KOMPAS_KEY에 인증키를 넣어 주세요.")
        run(k, None if args.missing_only else args.max_age_days, log=lambda m: print(m, flush=True))
    else:
        _gui()
