"""6 설계유속 — 가까운 조류 예보지점의 최강 조류(프로그램 안 자료) + 5 설계풍속으로 계산한 취송류."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from constants import ACCENT, SURF2, BORDER, LABEL, TEXT_DIM, F_LABEL, F_LABEL_B
from widgets import section_label, field_entry, primary_button, card_frame

import calc_current as cc
import source_current as sc
from schema import make_record
from tabs.common import banner, site_text, note_label, kv_row, make_tree
from tabs.manual_input import ManualCard

COLORS = {"tidal": "#60a5fa", "wind": "#fb923c", "total": "#f87171"}


def _deg(d):
    names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return f"{d:.0f}° ({names[int((d % 360) / 22.5 + 0.5) % 16]})"


class CurrentTabMixin:
    def _build_current_tab(self, parent):
        self._crnt_site_var = ctk.StringVar()
        banner(parent, self._crnt_site_var)
        self._crnt_sel = None

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._build_crnt_station_card(left).pack(fill="x", pady=(0, 8))
        self._build_crnt_rule_card(left).pack(fill="x")
        self._crnt_manual = ManualCard(left, "직접 입력 — 설계유속 (표층)", [
            ("current_tidal_max", "표층 조류 (최강)", True, None), ("current_tidal_dir", "조류 유향 (°)", False, None),
            ("current_wind_50yr", "50년 취송류 (표층)", True, None), ("current_wind_1yr", "1년 취송류 (표층)", True, None),
            ("current_shear_exp", "조류 연직분포 지수 α", True, cc.DEFAULT_ALPHA),
            ("current_wind_depth", "취송류 소멸 깊이 d0", True, 20.0)],
            self._on_crnt_manual, "설계유속(표층) = 조류 + 취송류로 계산합니다. 합계 유속만 있으면 조류 칸에 합계, 취송류 칸에 0.")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_crnt_result_card(right).pack(fill="x", pady=(0, 8))
        prof = card_frame(right)
        prof.pack(fill="both", expand=True)
        section_label(prof, "50년 설계유속 수심별 분포").pack(anchor="w", padx=14, pady=(12, 6))
        self._crnt_canvas = tk.Canvas(prof, bg=SURF2, highlightthickness=0)
        self._crnt_canvas.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._crnt_canvas.bind("<Configure>", lambda e: self._draw_crnt_profile())

    # ── 예보지점 ──

    def _build_crnt_station_card(self, parent):
        card = card_frame(parent)
        section_label(card, "조류 예보지점 (가까운 순, 클릭해서 바꿀 수 있음)").pack(anchor="w", padx=14, pady=(12, 6))
        self._crnt_tree = make_tree(card, [("name", "예보지점", 120), ("code", "코드", 90), ("km", "거리 (km)", 80),
                                           ("period", "예보 기간", 190), ("fetched", "받은 날", 100)], height=6)
        self._crnt_tree.pack(fill="x", padx=14, pady=(0, 8))
        self._crnt_tree.bind("<<TreeviewSelect>>", self._on_crnt_pick)

        section_label(card, "최강 창 · 낙조류").pack(anchor="w", padx=14, pady=(6, 4))
        self._crnt_info = {k: ctk.StringVar(value="-") for k in ("period", "A", "B", "max")}
        for k, label in [("period", "예보 기간 / 최강류 횟수"), ("A", "방향 무리 1"), ("B", "방향 무리 2"), ("max", "가장 센 조류")]:
            kv_row(card, label, self._crnt_info[k], width=170)
        note_label(card, "유향은 흘러가는 방향입니다. 자료에 창조 · 낙조 구분이 없어 방향으로 두 무리로 나눴습니다."
                   ).pack(anchor="w", padx=14, pady=(4, 4))
        note_label(card, f"출처: {sc.SOURCE_NAME}").pack(anchor="w", padx=14, pady=(0, 12))
        return card

    def _on_crnt_pick(self, event=None):
        sel = self._crnt_tree.selection()
        site = self.project.site()
        if not sel or not site or (self._crnt_sel and self._crnt_sel[1] == sel[0]):
            return
        self._crnt_sel = (site, sel[0])
        self.refresh_current_tab()

    # ── 취송류 · 연직분포 ──

    def _build_crnt_rule_card(self, parent):
        card = card_frame(parent)
        section_label(card, "취송류 · 수심별 분포 기준").pack(anchor="w", padx=14, pady=(12, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(row, text="취송류 기준", font=F_LABEL, text_color=LABEL, width=170, anchor="w").pack(side="left")
        self._crnt_rule = ctk.StringVar(value=cc.DEFAULT_RULE)
        ctk.CTkOptionMenu(row, variable=self._crnt_rule, values=list(cc.WIND_RULES), fg_color=SURF2, width=320,
                          command=lambda v: self.refresh_current_tab()).pack(side="left")
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(row2, text="조류 분포 지수 α", font=F_LABEL, text_color=LABEL, width=170, anchor="w").pack(side="left")
        self._crnt_alpha = ctk.StringVar(value=f"{cc.DEFAULT_ALPHA:.3f}")
        e = field_entry(row2, self._crnt_alpha, "0.143")
        e.configure(width=100)
        e.pack(side="left")
        e.bind("<FocusOut>", lambda ev: self.refresh_current_tab())
        e.bind("<Return>", lambda ev: self.refresh_current_tab())
        ctk.CTkLabel(row2, text="기본 1/7 = 0.143 (IEC · DNV)", font=F_LABEL, text_color=TEXT_DIM).pack(side="left", padx=8)
        self._crnt_inputs = {k: ctk.StringVar(value="-") for k in ("wind", "depth")}
        kv_row(card, "쓰는 풍속 (5 설계풍속)", self._crnt_inputs["wind"], width=170)
        kv_row(card, "쓰는 수심 (3 수심)", self._crnt_inputs["depth"], width=170)
        note_label(card, "취송류 = k × 풍속 U10.").pack(anchor="w", padx=14, pady=(4, 12))
        return card

    def _crnt_alpha_value(self):
        try:
            a = float(self._crnt_alpha.get())
            return a if 0 < a < 1 else None
        except ValueError:
            return None

    # ── 결과 ──

    def _build_crnt_result_card(self, parent):
        card = card_frame(parent)
        section_label(card, "설계유속 (표층 = 조류 + 취송류)").pack(anchor="w", padx=14, pady=(12, 6))
        self._crnt_res = {k: ctk.StringVar(value="-") for k in ("tidal", "wind", "u50", "u1")}
        for k, label in [("tidal", "최강 조류"), ("wind", "취송류 50년 / 1년"), ("u50", "50년 설계유속 (표층)"),
                         ("u1", "1년 설계유속 (표층)")]:
            kv_row(card, label, self._crnt_res[k], width=170)
        self._crnt_hint = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._crnt_hint, font=F_LABEL, text_color=LABEL, anchor="w", justify="left",
                     wraplength=600).pack(fill="x", padx=14, pady=(6, 0))
        self._crnt_adopt_btn = primary_button(card, "이 값을 반영", self._on_crnt_adopt, width=0)
        self._crnt_adopt_btn.pack(fill="x", padx=14, pady=(8, 6))
        self._crnt_adopted_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._crnt_adopted_var, font=F_LABEL_B, text_color=ACCENT, anchor="w",
                     justify="left", wraplength=600).pack(fill="x", padx=14, pady=(0, 12))
        return card

    def _crnt_state(self):
        """계산에 필요한 값 모음. 없는 부분은 None. 자료가 있는 지점이 하나도 없으면 None."""
        site = self.project.site()
        near = sc.nearest_stations(*site) if site else []
        if not near:
            return None
        if not self._crnt_sel or self._crnt_sel[0] != site:
            self._crnt_sel = (site, near[0][0]["code"])
        st, km = next(((s, d) for s, d in near if s["code"] == self._crnt_sel[1]), near[0])
        rule = cc.WIND_RULES[self._crnt_rule.get()]
        s = {"site": site, "near": near, "st": st, "km": km, "rule": rule, "depth": self.project.value("water_depth"),
             "u50": self.project.value("wind_speed_50yr"), "u1": self.project.value("wind_speed_1yr"),
             "alpha": self._crnt_alpha_value()}
        if s["u50"] is not None and s["u1"] is not None:
            s["tidal"] = st["max"]
            s["w50"], s["w1"] = cc.wind_surface(rule["k"], s["u50"]), cc.wind_surface(rule["k"], s["u1"])
            s["t50"], s["t1"] = s["tidal"] + s["w50"], s["tidal"] + s["w1"]
        return s

    def _on_crnt_manual(self):
        card = self._crnt_manual
        vals, errs = card.parse()
        if not errs:
            errs += [f"{k}: 0 이상이어야 합니다" for k in ("current_tidal_max", "current_wind_50yr", "current_wind_1yr")
                     if vals[k] < 0]
            if not 0 < vals["current_shear_exp"] < 1:
                errs.append("조류 연직분포 지수 α는 0과 1 사이입니다 (1/7 = 0.143)")
            if vals["current_wind_depth"] <= 0:
                errs.append("취송류 소멸 깊이는 0보다 커야 합니다")
        if errs:
            messagebox.showerror("입력 확인", "\n".join(errs))
            return
        if "current_tidal_dir" not in vals:
            self.project.drop("current_tidal_dir")      # 예보지점 유향이 직접 입력 유속과 섞이지 않게
        t = vals["current_tidal_max"]
        recs = card.records(self.project, vals)
        recs.update(card.records(self.project, {
            "current_surface_50yr": round(t + vals["current_wind_50yr"], 3),
            "current_surface_1yr": round(t + vals["current_wind_1yr"], 3)}, {
            "current_surface_50yr": f"직접 입력 조류 {t:g} + 50년 취송류 {vals['current_wind_50yr']:g} (같은 방향으로 봄)",
            "current_surface_1yr": f"직접 입력 조류 {t:g} + 1년 취송류 {vals['current_wind_1yr']:g} (같은 방향으로 봄)"}))
        self.project.set_many(recs)
        self.set_status(f"설계유속을 직접 입력값으로 반영했습니다 — 50년 {recs['current_surface_50yr']['value']:g} / "
                        f"1년 {recs['current_surface_1yr']['value']:g} m/s.")

    def refresh_current_tab(self):
        site = self.project.site()
        self._crnt_site_var.set(site_text(site))
        self._crnt_manual.refresh(self.project)
        self._crnt_tree.delete(*self._crnt_tree.get_children())
        s = self._crnt_state()
        if not s:
            for v in list(self._crnt_info.values()) + list(self._crnt_res.values()) + list(self._crnt_inputs.values()):
                v.set("-")
            self._crnt_hint.set("")
            self._crnt_adopt_btn.configure(state="disabled")
            self._show_crnt_adopted()
            self._draw_crnt_profile()
            return

        for st, km in s["near"]:
            self._crnt_tree.insert("", "end", iid=st["code"], values=(
                st["name"], st["code"], f"{km:.1f}", f"{st['from'][:10]} ~ {st['to'][:10]}", st["fetched"]))
        self._crnt_tree.selection_set(s["st"]["code"])

        st = s["st"]
        self._crnt_info["period"].set(f"{st['from'][:10]} ~ {st['to'][:10]} / {st['count']}회")
        for g in ("A", "B"):
            v = st["groups"].get(g)
            self._crnt_info[g].set(f"최대 {v['max']:.2f} m/s → {_deg(v['max_dir'])}, 평균 {v['mean']:.2f} m/s ({v['n']}회)" if v else "-")
        self._crnt_info["max"].set(f"{st['max']:.2f} m/s → {_deg(st['max_dir'])}  ({st['max_time']})")

        self._crnt_inputs["wind"].set(f"50년 {s['u50']} / 1년 {s['u1']} m/s" if s["u50"] is not None
                                      else "없음 — 5 설계풍속 탭에서 먼저 반영하세요")
        self._crnt_inputs["depth"].set(f"{s['depth']} m" if s["depth"] is not None
                                       else "없음 — 3 수심을 반영하면 분포 그림이 그려집니다")

        if "tidal" in s:
            self._crnt_res["tidal"].set(f"{s['tidal']:.2f} m/s → {_deg(st['max_dir'])}")
            self._crnt_res["wind"].set(f"{s['w50']:.2f} / {s['w1']:.2f} m/s  (k = {s['rule']['k']})")
            self._crnt_res["u50"].set(f"{s['t50']:.2f} m/s")
            self._crnt_res["u1"].set(f"{s['t1']:.2f} m/s")
            self._crnt_hint.set("" if s["alpha"] else "조류 분포 지수 α는 0과 1 사이 숫자로 넣어 주세요.")
            self._crnt_adopt_btn.configure(state="normal" if s["alpha"] else "disabled")
        else:
            for v in self._crnt_res.values():
                v.set("-")
            self._crnt_hint.set("5 설계풍속을 반영하면 취송류와 설계유속이 계산됩니다.")
            self._crnt_adopt_btn.configure(state="disabled")
        self._show_crnt_adopted()
        self._draw_crnt_profile()

    def _show_crnt_adopted(self):
        r50, r1 = self.project.get("current_surface_50yr"), self.project.get("current_surface_1yr")
        self._crnt_adopted_var.set(f"반영됨: 50년 {r50['value']} m/s / 1년 {r1['value']} m/s" if r50 and r1 else "")

    def _on_crnt_adopt(self):
        s = self._crnt_state()
        st, rule, site = s["st"], s["rule"], s["site"]
        src = sc.source_text(st)
        st_basis = (f"예보지점 ({st['lat']:.4f}, {st['lon']:.4f}), 설치위치에서 {s['km']:.1f} km, "
                    f"예보 기간 최강류 {st['count']}회 중 최대 ({st['max_time']})")
        wind_basis = f"k = {rule['k']} ({rule['ref']}) × 해상풍 U10"

        def rec(key, value, source, basis, ref=""):
            return make_record(key, round(value, 3), source, basis, ref=ref, site=site)

        self.project.set_many({
            "current_tidal_max": rec("current_tidal_max", s["tidal"], src, f"{st_basis}, 표층 값으로 씀", sc.BASE_URL),
            "current_tidal_dir": rec("current_tidal_dir", st["max_dir"], src, f"가장 센 조류의 유향(흘러가는 방향). {st_basis}", sc.BASE_URL),
            "current_wind_50yr": rec("current_wind_50yr", s["w50"], rule["ref"], f"{wind_basis}: {rule['k']} × {s['u50']} m/s"),
            "current_wind_1yr": rec("current_wind_1yr", s["w1"], rule["ref"], f"{wind_basis}: {rule['k']} × {s['u1']} m/s"),
            "current_surface_50yr": rec("current_surface_50yr", s["t50"], f"{src} + {rule['ref']}",
                                        f"조류 {s['tidal']:.3f} + 취송류 {s['w50']:.3f} (같은 방향으로 봄)"),
            "current_surface_1yr": rec("current_surface_1yr", s["t1"], f"{src} + {rule['ref']}",
                                       f"조류 {s['tidal']:.3f} + 취송류 {s['w1']:.3f} (같은 방향으로 봄)"),
            "current_shear_exp": rec("current_shear_exp", s["alpha"], "IEC 61400-3-1 / DNV-RP-C205",
                                     "조류 연직분포 U(z) = U0 · ((d + z) / d)^α"),
            "current_wind_depth": rec("current_wind_depth", rule["d0"], rule["ref"],
                                      f"취송류가 0이 되는 깊이 {rule['d0']:g} m (수심보다 깊으면 수심까지)"),
        })
        self.set_status(f"설계유속을 반영했습니다 — 50년 {s['t50']:.2f} m/s / 1년 {s['t1']:.2f} m/s (지점 {st['name']}).")

    # ── 수심별 분포 그림 ──

    def _draw_crnt_profile(self):
        cv = self._crnt_canvas
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        s = self._crnt_state() if self.project.site() else None
        if not s or "tidal" not in s or not s["depth"] or not s["alpha"] or w < 80 or h < 80:
            cv.create_text(w / 2, h / 2, text="조류, 5 설계풍속, 3 수심이 모두 있으면 분포가 그려집니다", fill=TEXT_DIM, font=F_LABEL)
            return
        rows = cc.profile(s["tidal"], s["w50"], s["depth"], s["rule"]["d0"], s["alpha"], n=40)
        umax = max(r[3] for r in rows) * 1.15
        x0, x1, y0, y1 = 70, w - 20, 34, h - 30
        X = lambda u: x0 + u / umax * (x1 - x0)                 # noqa: E731
        Y = lambda z: y0 + (-z) / s["depth"] * (y1 - y0)       # noqa: E731
        cv.create_rectangle(x0, y0, x1, y1, outline=BORDER)
        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            z = -s["depth"] * frac
            cv.create_line(x0, Y(z), x1, Y(z), fill=BORDER, dash=".")
            cv.create_text(x0 - 6, Y(z), text="0 m" if frac == 0 else f"-{s['depth'] * frac:.0f} m", anchor="e", fill=LABEL, font=F_LABEL)
        step = 0.5 if umax > 1.5 else 0.25
        u = 0.0
        while u <= umax:
            cv.create_text(X(u), y1 + 12, text=f"{u:.2f}", fill=LABEL, font=F_LABEL)
            u += step
        d0 = min(s["rule"]["d0"], s["depth"])
        cv.create_line(x0, Y(-d0), x1, Y(-d0), fill=COLORS["wind"], dash="-")
        cv.create_text(x1 - 4, Y(-d0) - 8, text=f"취송류 소멸 깊이 {d0:.0f} m", anchor="e", fill=COLORS["wind"], font=F_LABEL)
        for idx, key in ((1, "tidal"), (2, "wind"), (3, "total")):
            pts = []
            for r in rows:
                pts += [X(r[idx]), Y(r[0])]
            cv.create_line(*pts, fill=COLORS[key], width=2 if key != "total" else 3)
        for i, (key, label) in enumerate((("total", f"합계 {s['t50']:.2f} m/s (표층)"), ("tidal", f"조류 {s['tidal']:.2f}"),
                                          ("wind", f"취송류 {s['w50']:.2f}"))):
            lx = x0 + 8 + i * 170
            cv.create_line(lx, 14, lx + 22, 14, fill=COLORS[key], width=3)
            cv.create_text(lx + 28, 14, text=label, anchor="w", fill=COLORS[key], font=F_LABEL)
        cv.create_text(x1, y1 + 12, text="m/s", anchor="e", fill=LABEL, font=F_LABEL)
