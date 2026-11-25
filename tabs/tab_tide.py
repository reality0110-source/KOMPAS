"""2 설계조위 — 가까운 조위관측소의 천문조 + 기준서 기록에서 고른 폭풍해일고 → HSWL / LSWL.

해일고는 자동으로 고르지 않습니다. 후보 표에서 고르거나 직접 넣어야 계산 · 반영됩니다.
"""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from constants import ACCENT, SURF2, BORDER, LABEL, TEXT_DIM, WARN, F_LABEL, F_LABEL_B
from widgets import section_label, field_entry, primary_button, secondary_button, card_frame

import source_tide as kt
from schema import make_record
from tabs.common import banner, site_text, note_label, kv_row, make_tree, fmt
from tabs.manual_input import ManualCard

COLORS = {"hswl": "#f87171", "hat": "#fb923c", "msl": "#34d399", "lat": "#60a5fa", "lswl": "#c084fc", "record": WARN}


class TideTabMixin:
    def _build_tide_tab(self, parent):
        self._tide_site_var = ctk.StringVar()
        banner(parent, self._tide_site_var)
        self._tide_sel = None
        self._tide_surge = None

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_tide_station_card(left).pack(fill="x", pady=(0, 8))
        self._build_tide_surge_card(left).pack(fill="x")
        self._tide_manual = ManualCard(left, "직접 입력 — 설계조위 (D.L. 기준)", [
            ("tide_hswl", "HSWL 설계고조위", True, None), ("tide_hat", "HAT 최고천문조위", True, None),
            ("tide_msl", "MSL 평균해수면", True, None), ("tide_lat", "LAT 최저천문조위", True, None),
            ("tide_lswl", "LSWL 설계저조위", True, None)],
            self._on_tide_manual, "해일고는 HSWL − HAT, LSWL − LAT로 함께 기록합니다.")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_tide_result_card(right).pack(fill="x", pady=(0, 8))
        diagram = card_frame(right)
        diagram.pack(fill="both", expand=True)
        section_label(diagram, "설계조위 도식 (관측소 D.L. 기준)").pack(anchor="w", padx=14, pady=(12, 6))
        self._tide_canvas = tk.Canvas(diagram, bg=SURF2, highlightthickness=0)
        self._tide_canvas.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self._tide_canvas.bind("<Configure>", lambda e: self._draw_tide_diagram())
        note_label(diagram, f"출처: {kt.STANDARD} 해설 표 4.4-3 · 4.4-6 · 4.4-7 · 4.4-8").pack(anchor="w", padx=14, pady=(0, 10))

    # ── 조위관측소 ──

    def _build_tide_station_card(self, parent):
        card = card_frame(parent)
        section_label(card, "조위관측소 (가까운 순, 클릭해서 바꿀 수 있음)").pack(anchor="w", padx=14, pady=(12, 6))
        self._tide_st_tree = make_tree(card, [("name", "관측소", 100), ("coord", "좌표", 150), ("km", "거리 (km)", 80),
                                              ("period", "조화분석 관측기간", 190)], height=5)
        self._tide_st_tree.pack(fill="x", padx=14, pady=(0, 8))
        self._tide_st_tree.bind("<<TreeviewSelect>>", self._on_tide_station_pick)

        section_label(card, "천문조 (해설 표 4.4-3 비조화상수)").pack(anchor="w", padx=14, pady=(6, 4))
        self._tide_astro = {k: ctk.StringVar(value="-") for k in ("hat", "hwost", "msl", "lat", "range", "record")}
        for k, label in [("hat", "HAT = 약최고고조위"), ("hwost", "대조평균고조위"), ("msl", "평균해면 MSL"),
                         ("lat", "LAT = 기본수준면"), ("range", "대조차 / 조석형태수"), ("record", "최극조위 (표 4.4-8)")]:
            kv_row(card, label, self._tide_astro[k], width=170)
        ctk.CTkFrame(card, fg_color="transparent", height=10).pack()
        return card

    def _on_tide_station_pick(self, event=None):
        sel = self._tide_st_tree.selection()
        site = self.project.site()
        if not sel or not site or (self._tide_sel and self._tide_sel[1] == sel[0]):
            return
        self._tide_sel = (site, sel[0])
        self.refresh_tide_tab()

    def _current_tide_station(self):
        site = self.project.site()
        if not site:
            return None
        near = kt.nearest_stations(*site, n=5)
        if not self._tide_sel or self._tide_sel[0] != site:
            self._tide_sel = (site, near[0][0]["name"])
            self._tide_surge = None
        for st, km in near:
            if st["name"] == self._tide_sel[1]:
                return st, km, near
        return near[0][0], near[0][1], near

    # ── 폭풍해일고 ──

    def _build_tide_surge_card(self, parent):
        card = card_frame(parent)
        section_label(card, "폭풍해일고 (기준서 기록 중 설치위치에서 가까운 곳)").pack(anchor="w", padx=14, pady=(12, 4))
        note_label(card, "후보를 클릭해 고르거나 아래에 직접 넣으세요. 고르기 전에는 HSWL / LSWL이 계산되지 않습니다."
                   ).pack(anchor="w", padx=14, pady=(0, 6))
        self._tide_sg_tree = make_tree(card, [("table", "근거 표", 190), ("place", "위치", 90), ("km", "거리 (km)", 75),
                                              ("pos", "+ 해일 (m)", 80), ("neg", "− 해일 (m)", 80),
                                              ("period", "기록 기간", 140)], height=9)
        self._tide_sg_tree.tag_configure("sel", background="#0f3d33")
        self._tide_sg_tree.pack(fill="x", padx=14, pady=(0, 6))
        self._tide_sg_tree.bind("<<TreeviewSelect>>", self._on_tide_surge_pick)
        self._tide_sg_note = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._tide_sg_note, font=F_LABEL, text_color=LABEL, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=14, pady=(0, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 12))
        self._tide_man = {k: ctk.StringVar() for k in ("pos", "neg", "src")}
        for key, ph, w in [("pos", "+ 해일 (m)", 100), ("neg", "− 해일 (m, 음수)", 130),
                           ("src", "출처 (예: ○○ 빈도분석 보고서, 2026)", 330)]:
            e = field_entry(row, self._tide_man[key], ph)
            e.configure(width=w)
            e.pack(side="left", padx=(0, 6))
        secondary_button(row, "이 해일고 쓰기", self._on_tide_manual_surge, width=120).pack(side="left")
        return card

    def _on_tide_surge_pick(self, event=None):
        sel = self._tide_sg_tree.selection()
        site = self.project.site()
        if not sel or not site:
            return
        cand = next((c for c in kt.surge_candidates(*site) if c["id"] == sel[0]), None)
        if cand and (not self._tide_surge or self._tide_surge["id"] != cand["id"]):
            self._tide_surge = cand
            self.refresh_tide_tab()

    def _on_tide_manual_surge(self):
        try:
            pos = float(self._tide_man["pos"].get().strip())
            neg = float(self._tide_man["neg"].get().strip())
        except ValueError:
            self.set_status("해일고는 숫자로 넣어 주세요 (− 해일은 음수, 예: -0.86).")
            return
        src = self._tide_man["src"].get().strip()
        if not src:
            self.set_status("직접 넣은 해일고의 출처를 적어 주세요.")
            return
        if pos < 0 or neg > 0:
            self.set_status("+ 해일은 0 이상, − 해일은 0 이하로 넣어 주세요.")
            return
        self._tide_surge = {"id": "manual", "table": "직접 입력", "place": "-", "km": 0.0, "pos": pos, "neg": neg,
                            "period": "-", "note": src, "ref": src}
        self.refresh_tide_tab()

    # ── 결과 ──

    def _build_tide_result_card(self, parent):
        card = card_frame(parent)
        section_label(card, "설계조위 (HSWL = HAT + 해일, LSWL = LAT + 해일)").pack(anchor="w", padx=14, pady=(12, 6))
        self._tide_res = {k: ctk.StringVar(value="-") for k in ("hswl", "astro", "lswl", "surge")}
        for k, label in [("hswl", "HSWL 설계고조위"), ("astro", "HAT / MSL / LAT"), ("lswl", "LSWL 설계저조위"),
                         ("surge", "쓴 해일고")]:
            kv_row(card, label, self._tide_res[k], width=170)
        self._tide_adopt_btn = primary_button(card, "이 값을 반영", self._on_tide_adopt, width=0)
        self._tide_adopt_btn.pack(fill="x", padx=14, pady=(12, 6))
        self._tide_adopted_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._tide_adopted_var, font=F_LABEL_B, text_color=ACCENT, anchor="w",
                     justify="left", wraplength=600).pack(fill="x", padx=14, pady=(0, 12))
        return card

    def _tide_state(self):
        """(관측소, 거리, 가까운 목록, 천문조, 해일, 설계조위) — 계산할 수 없는 부분은 None."""
        cur = self._current_tide_station()
        if not cur:
            return None
        st, km, near = cur
        astro = kt.astro_levels(st)
        levels = kt.design_levels(astro, self._tide_surge["pos"], self._tide_surge["neg"]) if self._tide_surge else None
        return st, km, near, astro, self._tide_surge, levels

    def _on_tide_manual(self):
        card = self._tide_manual
        vals, errs = card.parse()
        if not errs:
            order = [("tide_hswl", "HSWL"), ("tide_hat", "HAT"), ("tide_msl", "MSL"), ("tide_lat", "LAT"), ("tide_lswl", "LSWL")]
            errs += [f"{a[1]} ≥ {b[1]} 이어야 합니다" for a, b in zip(order, order[1:]) if vals[a[0]] < vals[b[0]]]
        if errs:
            messagebox.showerror("입력 확인", "\n".join(errs))
            return
        recs = card.records(self.project, vals)
        pos, neg = vals["tide_hswl"] - vals["tide_hat"], vals["tide_lswl"] - vals["tide_lat"]
        recs.update(card.records(self.project, {"tide_surge_pos": round(pos, 3), "tide_surge_neg": round(neg, 3)},
                                 {"tide_surge_pos": "직접 입력한 HSWL − HAT", "tide_surge_neg": "직접 입력한 LSWL − LAT"}))
        self.project.set_many(recs)
        self.set_status(f"설계조위를 직접 입력값으로 반영했습니다 — HSWL {vals['tide_hswl']:g} / LSWL {vals['tide_lswl']:g} m.")

    def refresh_tide_tab(self):
        site = self.project.site()
        self._tide_site_var.set(site_text(site))
        self._tide_manual.refresh(self.project)
        for tree in (self._tide_st_tree, self._tide_sg_tree):
            tree.delete(*tree.get_children())
        state = self._tide_state()
        if not state:
            for v in list(self._tide_astro.values()) + list(self._tide_res.values()):
                v.set("-")
            self._tide_sg_note.set("")
            self._tide_adopt_btn.configure(state="disabled")
            self._show_tide_adopted()
            self._draw_tide_diagram()
            return
        st, km, near, astro, surge, levels = state

        for s, d in near:
            self._tide_st_tree.insert("", "end", iid=s["name"], values=(s["name"], f"{s['lat']:.3f}, {s['lon']:.3f}",
                                                                        f"{d:.1f}", s["period"]))
        self._tide_st_tree.selection_set(st["name"])

        ext = kt.extreme_of(st["name"])
        self._tide_astro["hat"].set(f"{astro['hat']:.3f} m")
        self._tide_astro["hwost"].set(f"{astro['hwost']:.3f} m")
        self._tide_astro["msl"].set(f"{astro['msl']:.3f} m")
        self._tide_astro["lat"].set(f"{astro['lat']:.3f} m")
        self._tide_astro["range"].set(f"{astro['spr']:.3f} m / {astro['form']}")
        self._tide_astro["record"].set(f"고 {ext['hhw']} m ({ext['hhw_date']}) / 저 {ext['llw']} m ({ext['llw_date']}), {ext['period']}"
                                       if ext else "이 관측소는 기록 없음")

        for c in kt.surge_candidates(*site):
            self._tide_sg_tree.insert("", "end", iid=c["id"], values=(
                c["table"], c["place"], f"{c['km']:.0f}", f"+{c['pos']:.2f}",
                fmt(c["neg"]) if c["neg"] is not None else "기록 없음", c["period"]),
                tags=("sel",) if surge and surge["id"] == c["id"] else ())
        if surge and surge["id"] != "manual":
            self._tide_sg_tree.selection_set(surge["id"])
        self._tide_sg_note.set(f"고른 것: [{surge['table']}] {surge['place']} — {surge['note']}" if surge else "고른 해일고 없음")

        self._tide_res["astro"].set(f"{astro['hat']:.3f} / {astro['msl']:.3f} / {astro['lat']:.3f} m")
        if levels:
            self._tide_res["hswl"].set(f"{levels['hswl']:.3f} m")
            self._tide_res["lswl"].set(f"{levels['lswl']:.3f} m" if levels["lswl"] is not None else "− 해일고가 있어야 합니다")
            neg_txt = f"{surge['neg']:.2f}" if surge["neg"] is not None else "없음"
            self._tide_res["surge"].set(f"+{surge['pos']:.2f} / {neg_txt} m  ({surge['table']}, {surge['place']})")
            self._tide_adopt_btn.configure(state="normal" if levels["lswl"] is not None else "disabled")
        else:
            for k in ("hswl", "lswl", "surge"):
                self._tide_res[k].set("해일고를 고르세요")
            self._tide_adopt_btn.configure(state="disabled")
        self._show_tide_adopted()
        self._draw_tide_diagram()

    def _show_tide_adopted(self):
        h, l = self.project.get("tide_hswl"), self.project.get("tide_lswl")
        self._tide_adopted_var.set(f"반영됨: HSWL {h['value']} m / LSWL {l['value']} m" if h and l else "")

    def _on_tide_adopt(self):
        st, km, _, astro, surge, levels = self._tide_state()
        site = self.project.site()
        src = kt.source()
        st_basis = f"조위관측소 {st['name']} ({st['lat']:.3f}, {st['lon']:.3f}), 설치위치에서 {km:.1f} km, 관측소 D.L. 기준"
        surge_basis = f"[{surge['table']}] {surge['place']} ({surge['km']:.0f} km) — {surge['note']}"
        surge_src = f"직접 입력 — {surge['ref']}" if surge["id"] == "manual" else kt.STANDARD

        def rec(key, value, source, basis, ref):
            return make_record(key, round(value, 3), source, basis, ref=ref, site=site)

        self.project.set_many({
            "tide_hat": rec("tide_hat", astro["hat"], kt.STANDARD, f"약최고고조위(AHHW). {st_basis}", src["nonharmonic"]),
            "tide_msl": rec("tide_msl", astro["msl"], kt.STANDARD, f"평균해면. {st_basis}", src["nonharmonic"]),
            "tide_lat": rec("tide_lat", astro["lat"], kt.STANDARD, f"기본수준면(D.L. = 약최저저조위). {st_basis}", src["datum"]),
            "tide_surge_pos": rec("tide_surge_pos", surge["pos"], surge_src, surge_basis, surge["ref"]),
            "tide_surge_neg": rec("tide_surge_neg", surge["neg"], surge_src, surge_basis, surge["ref"]),
            "tide_hswl": rec("tide_hswl", levels["hswl"], f"{kt.STANDARD} + {surge_src}" if surge["id"] == "manual" else kt.STANDARD,
                             f"HAT {astro['hat']} + 해일 {surge['pos']}. {st_basis}. {surge_basis}", surge["ref"]),
            "tide_lswl": rec("tide_lswl", levels["lswl"], f"{kt.STANDARD} + {surge_src}" if surge["id"] == "manual" else kt.STANDARD,
                             f"LAT {astro['lat']} + 해일 {surge['neg']}. {st_basis}. {surge_basis}", surge["ref"]),
        })
        self.set_status(f"설계조위를 반영했습니다 — HSWL {levels['hswl']} m / LSWL {levels['lswl']} m (관측소 {st['name']}).")

    # ── 도식 ──

    def _draw_tide_diagram(self):
        cv = self._tide_canvas
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        state = self._tide_state()
        if not state or w < 50 or h < 50:
            cv.create_text(w / 2, h / 2, text="설치위치를 정하면 조위가 그려집니다", fill=TEXT_DIM, font=F_LABEL)
            return
        st, _, _, astro, surge, levels = state
        ext = kt.extreme_of(st["name"])
        lines = []          # (이름, 값, 색, 점선 모양, 굵기) — 설계값 · MSL = 실선, 천문조 = 긴 점선, 기록 = 잔 점선
        if levels:
            lines.append(("HSWL", levels["hswl"], COLORS["hswl"], None, 2))
        if ext:
            lines.append((f"최고극조위 ({ext['hhw_date'][:4]})", ext["hhw"], COLORS["record"], ".", 1))
        lines += [("HAT", astro["hat"], COLORS["hat"], "-", 2), ("MSL", astro["msl"], COLORS["msl"], None, 2),
                  ("LAT (D.L.)", astro["lat"], COLORS["lat"], "-", 2)]
        if ext:
            lines.append((f"최저극조위 ({ext['llw_date'][:4]})", ext["llw"], COLORS["record"], ".", 1))
        if levels and levels["lswl"] is not None:
            lines.append(("LSWL", levels["lswl"], COLORS["lswl"], None, 2))

        groups = []
        for label, v, color, dash, width in sorted(lines, key=lambda t: -t[1]):
            if groups and abs(groups[-1]["v"] - v) < 0.005:
                groups[-1]["labels"].append(label)
            else:
                groups.append({"v": v, "labels": [label], "color": color, "dash": dash, "width": width})

        top = max(gr["v"] for gr in groups) + 0.6
        bot = min(gr["v"] for gr in groups) - 0.6
        y = lambda v: 36 + (top - v) / (top - bot) * (h - 52)      # noqa: E731
        x0, x1 = 80, w - 210
        cv.create_rectangle(x0, y(astro["msl"]), x1, h - 16, fill="#10304a", outline="")
        cv.create_line(x0, 36, x0, h - 16, fill=BORDER)
        gap = 17
        label_y = []
        for gr in groups:
            ty = y(gr["v"])
            if label_y and ty < label_y[-1] + gap:
                ty = label_y[-1] + gap
            label_y.append(ty)
        limit = h - 10
        for i in range(len(label_y) - 1, -1, -1):
            below = label_y[i + 1] - gap if i + 1 < len(label_y) else limit
            label_y[i] = min(label_y[i], below)

        for gr, ty in zip(groups, label_y):
            yy = y(gr["v"])
            cv.create_line(x0, yy, x1, yy, fill=gr["color"], width=gr["width"], dash=gr["dash"])
            if abs(ty - yy) > 0.5:
                cv.create_line(x1, yy, x1 + 14, ty, fill=gr["color"])
                cv.create_line(x0, yy, x0 - 10, ty, fill=gr["color"])
            cv.create_text(x0 - 12, ty, text=f"{gr['v']:+.2f}", anchor="e", fill=gr["color"], font=F_LABEL_B)
            cv.create_text(x1 + 18, ty, text=" = ".join(gr["labels"]), anchor="w", fill=gr["color"], font=F_LABEL)
        cv.create_text(8, 14, text=f"관측소: {st['name']}  (단위 m, D.L. 기준)", anchor="w", fill=LABEL, font=F_LABEL)
