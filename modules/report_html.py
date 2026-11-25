"""결과 정리 HTML — 반영된 값을 항목마다 값 · 단위 · 출처 · 근거와 함께 한 장으로 (브라우저에서 열고 인쇄하면 PDF).

GUI 없이도 부를 수 있습니다: build(project, version) → HTML 글
"""
from datetime import date
from html import escape

import coord
from schema import FIELDS, SECTIONS, TABLE_KEYS, fields_in

CSS = """
body { font-family: "Noto Sans KR", "Malgun Gothic", sans-serif; color: #1b2430; margin: 32px auto; max-width: 1100px;
       padding: 0 20px; font-size: 13px; line-height: 1.5; }
h1 { font-size: 22px; margin: 0 0 4px; color: #0b6b5b; }
h2 { font-size: 16px; margin: 28px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #00c9a7; }
.meta { color: #5b6b7c; margin-bottom: 8px; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 4px; }
th, td { border: 1px solid #d7dee6; padding: 5px 8px; vertical-align: top; }
th { background: #eef1f5; text-align: left; font-weight: bold; }
td.num { text-align: right; white-space: nowrap; }
td.c, th.c { text-align: center; white-space: nowrap; }
td.name { white-space: nowrap; }
.empty { color: #93a1b0; }
.dirs td, .dirs th { text-align: center; padding: 3px 6px; }
.dirs tr.gov td { background: #d7f5ee; font-weight: bold; }
footer { margin-top: 32px; color: #93a1b0; font-size: 11px; }
@media print { body { margin: 0; max-width: none; } h2 { break-after: avoid; } table { break-inside: auto; } }
"""


def _num(v, digits=3):
    if v is None:
        return "-"
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return escape(str(v))
    return escape((f"{v:.{digits}f}").rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


def _site_block(project):
    site = project.site()
    if not site:
        return '<p class="empty">설치위치가 없습니다.</p>'
    rec = project.get("site_lat")
    zone = coord.entered_utm_zone(rec.get("source"), rec.get("basis"))
    rows = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>"
                   for k, v in coord.format_all(*site, utm_zone=zone).items())
    rows += f"<tr><th>정한 방법</th><td>{escape(rec['source'])} {escape(rec.get('basis') or '')}</td></tr>"
    return f"<table>{rows}</table>"


def _section_table(project, sec):
    rows = []
    for f in fields_in(sec):
        if f.key in TABLE_KEYS:
            continue
        rec = project.get(f.key)
        if not rec:
            continue
        rows.append(f"<tr><td class='name'>{escape(f.name)}</td><td class='num'>{_num(rec['value'])}</td><td class='c'>{escape(f.unit)}</td>"
                    f"<td>{escape(rec.get('source') or '')}</td><td>{escape(rec.get('basis') or '')}</td></tr>")
    if not rows:
        return '<p class="empty">반영된 값이 없습니다.</p>'
    head = "<tr><th>항목</th><th>값</th><th class='c'>단위</th><th>출처</th><th>근거</th></tr>"
    return f"<table>{head}{''.join(rows)}</table>"


def _wave_dirs(project):
    rec = project.get("deepwave_table")
    if not rec:
        return ""
    t = rec["value"]
    rps = list(t["hs"])
    dirs = list(t["hs"][rps[0]])
    gov = project.value("deepwave_dir_50yr")
    head = "<tr><th>방향</th><th>1년 (추정)</th>" + "".join(f"<th>{escape(rp)}년</th>" for rp in rps) + "<th>50년 원인</th></tr>"
    body = ""
    for d in dirs:
        cells = f"<td>{_num(t['hs_1yr_est'].get(d))} / {_num(t['tp_1yr_est'].get(d))}</td>"
        cells += "".join(f"<td>{_num(t['hs'][rp][d])} / {_num(t['tp'][rp][d])}</td>" for rp in rps)
        cells += f"<td>{escape(str(t['cause'].get('50', {}).get(d, '-')))}</td>"
        body += f"<tr{' class=gov' if d == gov else ''}><td>{escape(d)}</td>{cells}</tr>"
    return (f"<p>재현주기 · 방향별 심해설계파 (Hs m / Tp s) — 출처: {escape(rec['source'])}, {escape(rec.get('basis') or '')}</p>"
            f"<table class='dirs'>{head}{body}</table>")


def _wind_dirs(project):
    rec = project.get("wind_table")
    if not rec:
        return ""
    t = rec["value"]
    rps = list(t["speed"])
    dirs = list(t["speed"][rps[0]])
    gov = project.value("wind_dir_50yr")
    head = "<tr><th>방향</th><th>1년 (추정)</th>" + "".join(f"<th>{escape(rp)}년</th>" for rp in rps) + "</tr>"
    body = ""
    for d in dirs:
        cells = f"<td>{_num(t['speed_1yr_est'].get(d))}</td>" + "".join(f"<td>{_num(t['speed'][rp][d])}</td>" for rp in rps)
        body += f"<tr{' class=gov' if d == gov else ''}><td>{escape(d)}</td>{cells}</tr>"
    return (f"<p>재현주기 · 방향별 해상풍 U10 (m/s) — 출처: {escape(rec['source'])}, {escape(rec.get('basis') or '')}</p>"
            f"<table class='dirs'>{head}{body}</table>")


def build(project, version=""):
    title = project.name or "해양환경 자료"
    parts = [f"<h1>KOMPAS — {escape(title)}</h1>",
             f"<div class='meta'>만든 날 {date.today().isoformat()}</div>",
             f"<h2>1 {escape(SECTIONS['1'])}</h2>", _site_block(project)]
    extra = {"4": _wave_dirs, "5": _wind_dirs}
    for sec in ("2", "3", "4", "5", "6"):
        parts.append(f"<h2>{sec} {escape(SECTIONS[sec])}</h2>")
        parts.append(_section_table(project, sec))
        if sec in extra:
            parts.append(extra[sec](project))
    parts.append(f"<footer>KOMPAS {escape(version)}</footer>")
    return ("<!DOCTYPE html>\n<html lang='ko'>\n<head>\n<meta charset='utf-8'>\n"
            f"<title>KOMPAS — {escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
            + "\n".join(parts) + "\n</body>\n</html>\n")


def counts(project):
    """(반영된 값 수, 전체 값 수) — 설치위치 제외"""
    keys = [k for k, f in FIELDS.items() if f.section != "1"]
    return sum(1 for k in keys if project.get(k)), len(keys)
