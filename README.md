# KOMPAS

**Korea Offshore Metocean Preliminary Assessment System** — 한국 해역 예비설계 해양환경 조회

좌표 하나를 찍으면 그 위치의 설계조위 · 수심 · 극한설계파고 · 설계풍속 · 설계유속을 공공자료에서 찾아,
값마다 자료 출처와 함께 정리합니다. 결과는 HTML 한 장으로 저장됩니다(브라우저에서 인쇄하면 PDF).

## 쓰는 자료

| 항목 | 자료 | 프로그램 안에 들어 있음 |
|---|---|---|
| 설계조위 | 항만 및 어항 설계기준 KDS 64 10 10: 2024, 해설 표 4.4-3 · 4.4-6 · 4.4-7 · 4.4-8 | 예 |
| 수심 | 국립해양조사원 자연과학용 수심정보 (공공데이터포털 API) — 평균해면 기준 → 조위관측소 평균해면 높이를 빼서 D.L. 기준으로 | 아니요 — 인증키가 있으면 측정점을 찾고, 없으면 직접 입력 |
| 극한설계파고 · 설계풍속 | 해양수산부 (2019) 빈도별 심해설계파 · 해상풍 제원, 전국 520개 격자점 | 예 |
| 설계유속 | 국립해양조사원 조류예보 최강창낙조 및 전류 (공공데이터포털 API), 지점마다 받은 날 · 예보 기간 | 예 |
| 지도 | © OpenStreetMap contributors, Leaflet (BSD-2-Clause) | 지도 부품만 |

국립해양조사원 자료(조류 · 수심)는 공공누리 제1유형(출처표시)입니다.

## 실행

- **exe (권장):** [Releases](https://github.com/reality0110-source/KOMPAS/releases)에서 `KOMPAS.exe`를 받아 더블클릭 — 설치 없음
- **소스로:** 파이썬 3.11 이상 + customtkinter (`pip install customtkinter`) → `실행.bat` 또는 `pythonw KOMPAS.pyw`
- Windows, Microsoft Edge 또는 Chrome (지도 창)
- 수심 측정점 자동 조회만 공공데이터포털 인증키가 필요합니다(3 수심 탭에서 한 번 입력, 이 컴퓨터에만 저장). 없으면 수심을 직접 입력합니다.

## 공식판

공식판은 이 저장소의 Releases에서만 배포합니다. 판마다 `KOMPAS.exe.sha256.txt`에 적힌 지문(SHA-256)과
받은 파일의 지문이 같으면 공식판입니다 (PowerShell: `Get-FileHash KOMPAS.exe`).

## 라이선스

Apache License 2.0 — `LICENSE`, `NOTICE`. 다른 사람이 만든 부품은 `THIRD_PARTY_NOTICES.md`와 `licenses` 폴더.
Apache 라이선스는 "KOMPAS"라는 이름을 쓸 권리를 주지 않습니다. 고친 판은 다른 이름으로 배포하고 고쳤다는 사실을 밝혀 주세요.

## 폴더

| 폴더 | 내용 |
|---|---|
| `modules` | 자료 찾기 · 계산 · 저장 · HTML |
| `tabs` | 화면(탭)마다 한 파일 |
| `ui` | 화면 색 · 글꼴 · 공용 부품 |
| `web` | 지도 페이지와 Leaflet |
| `data` | 프로그램 안에 넣어 둔 자료 |
| `tools` | `update_current.py` — 조류 자료(`data/tidal_current.json`)를 다시 받는 도구, `build_exe.py` — exe 만들기 |
| `licenses` | 다른 사람이 만든 부품의 라이선스 원문 |
