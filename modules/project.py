"""작업 데이터 — 변수 사전의 값들을 담고 파일(.kompas, 안은 JSON 글)로 저장 · 불러오기.

값이 바뀌면 등록된 화면들에 알려서(subscribe) 모든 탭이 같은 값을 보게 합니다.
"""
import json
from datetime import datetime
from pathlib import Path

import files
from schema import FIELDS, SCHEMA_VERSION, make_record

FILE_EXT = ".kompas"


class Project:
    def __init__(self):
        self.name = ""
        self.path = None
        self.values = {}
        self._listeners = []

    def subscribe(self, fn):
        self._listeners.append(fn)

    def _notify(self):
        for fn in self._listeners:
            fn()

    def get(self, key):
        return self.values.get(key)

    def value(self, key):
        rec = self.values.get(key)
        return rec["value"] if rec else None

    def set(self, key, record):
        self.set_many({key: record})

    def set_many(self, records):
        for key in records:
            if key not in FIELDS:
                raise KeyError(f"변수 사전에 없는 이름입니다: {key}")
        self.values.update(records)
        self._notify()

    def drop(self, *keys):
        """값을 뺌 (알림은 하지 않음 — 이어서 set_many를 부르는 곳에서 씀)"""
        for k in keys:
            self.values.pop(k, None)

    def site(self):
        lat, lon = self.value("site_lat"), self.value("site_lon")
        return (lat, lon) if lat is not None and lon is not None else None

    def set_site(self, lat, lon, source, basis=""):
        """설치위치를 바꾸고, 이전 좌표 기준으로 구한 값들은 지웁니다. 지운 개수를 돌려줌."""
        new_site = [lat, lon]
        stale = [k for k, r in self.values.items() if r.get("site") and r["site"] != new_site]
        for k in stale:
            del self.values[k]
        self.values["site_lat"] = make_record("site_lat", lat, source, basis)
        self.values["site_lon"] = make_record("site_lon", lon, source, basis)
        self._notify()
        return len(stale)

    def clear(self):
        self.name = ""
        self.path = None
        self.values = {}
        self._notify()

    def save(self, path):
        data = {"schema_version": SCHEMA_VERSION, "name": self.name,
                "saved_at": datetime.now().isoformat(timespec="seconds"), "values": self.values}
        files.write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
        self.path = str(path)

    def load(self, path):
        """불러온 뒤 변수 사전에 없는 이름 목록을 돌려줌 (그 값은 무시)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"파일 형식 버전이 다릅니다 (파일: {data.get('schema_version')}, 프로그램: {SCHEMA_VERSION})")
        values = data.get("values", {})
        unknown = [k for k in values if k not in FIELDS]
        self.values = {k: v for k, v in values.items() if k in FIELDS}
        self.name = data.get("name", "")
        self.path = str(path)
        self._notify()
        return unknown
