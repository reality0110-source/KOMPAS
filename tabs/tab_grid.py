"""4 극한설계파고 · 5 설계풍속 — 해수부(2019) 격자자료에서 설치위치와 가장 가까운 격자점.

두 탭은 같은 격자점을 쓰므로, 한 탭에서 격자점을 바꾸면 다른 탭도 같이 바뀝니다.
"""
from tkinter import messagebox

import customtkinter as ctk

from constants import ACCENT, RECOMMEND_BG
from widgets import section_label, primary_button, card_frame

import source_grid as g
from schema import make_record
from tabs.common import banner, site_text, note_label, kv_row, make_tree, fmt
from tabs.manual_input import ManualCard


class GridTabsMixin:
    def _build_grid_tab(self, parent, kind):
        site_var = ctk.StringVar()
        banner(parent, site_var)

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        near = card_frame(left)
        near.pack(fill="x", pady=(0, 8))
        section_label(near, "가까운 격자점 (클릭해서 바꿀 수 있음)").pack(anchor="w", padx=14, pady=(12, 6))
        near_tree = make_tree(near, [("id", "지점", 90), ("coord", "좌표", 150), ("dist", "거리 (km)", 80)], height=5)
        near_tree.pack(fill="x", padx=14, pady=(0, 14))
        near_tree.bind("<<TreeviewSelect>>", lambda e: self._on_grid_pick(near_tree))

        pick = card_frame(left)
        pick.pack(fill="both", expand=True)
        section_label(pick, "반영할 값").pack(anchor="w", padx=14, pady=(12, 6))
        if kind == "wave":
            rows = [("hs50", "50년 Hs"), ("tp50", "50년 Tp"), ("dir50", "50년 방향"), ("hs1", "1년 Hs (추정)"), ("tp1", "1년 Tp (추정)")]
        else:
            rows = [("u50", "50년 풍속 U10"), ("dir50", "50년 방향"), ("u1", "1년 풍속 U10 (추정)")]
        vals = {k: ctk.StringVar(value="-") for k, _ in rows}
        for k, label in rows:
            kv_row(pick, label, vals[k], width=150)
        btn = primary_button(pick, "이 값을 반영", self._on_wave_adopt if kind == "wave" else self._on_wind_adopt, width=0)
        btn.pack(fill="x", padx=14, pady=(12, 6))
        adopted_var = ctk.StringVar(value="")
        ctk.CTkLabel(pick, textvariable=adopted_var, text_color=ACCENT, anchor="w", justify="left",
                     wraplength=480).pack(fill="x", padx=14)
        note_label(pick, f"출처: {g.SOURCE_NAME}").pack(anchor="w", padx=14, pady=(10, 1))
        note_label(pick, f"{g.ONE_YR_BASIS}.").pack(anchor="w", padx=14, pady=(1, 14))

        if kind == "wave":
            manual = ManualCard(left, "직접 입력 — 심해설계파", [
                ("deepwave_hs_50yr", "50년 Hs", True, None), ("deepwave_tp_50yr", "50년 Tp", True, None),
                ("deepwave_dir_50yr", "50년 방향 (예: NW)", False, None),
                ("deepwave_hs_1yr", "1년 Hs", True, None), ("deepwave_tp_1yr", "1년 Tp", True, None)],
                self._on_wave_manual)
        else:
            manual = ManualCard(left, "직접 입력 — 해상풍 U10", [
                ("wind_speed_50yr", "50년 풍속 U10", True, None), ("wind_dir_50yr", "50년 방향 (예: N)", False, None),
                ("wind_speed_1yr", "1년 풍속 U10", True, None)],
                self._on_wind_manual)

        table = card_frame(body)
        table.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        rps = [str(rp) for rp in g.return_periods()]
        if kind == "wave":
            section_label(table, "재현주기 · 방향별 심해설계파  (Hs m / Tp s)").pack(anchor="w", padx=14, pady=(12, 6))
            cols = [("dir", "방향", 60), ("1", "1년(추정)", 95)] + [(rp, f"{rp}년", 85) for rp in rps] + [("cause", "50년 원인", 75)]
        else:
            section_label(table, "재현주기 · 방향별 해상풍 U10  (m/s)").pack(anchor="w", padx=14, pady=(12, 6))
            cols = [("dir", "방향", 60), ("1", "1년(추정)", 90)] + [(rp, f"{rp}년", 80) for rp in rps]
        tree = make_tree(table, cols, height=17)
        tree.tag_configure("gov", background=RECOMMEND_BG)
        tree.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        note_label(table, "강조된 행 = 50년 최댓값 방향." + (" 원인 EC = 온대저기압, TP = 태풍." if kind == "wave" else "")
                   ).pack(anchor="w", padx=14, pady=(0, 12))

        if not hasattr(self, "_grid_ui"):
            self._grid_ui = {}
            self._grid_sel = None
        self._grid_ui[kind] = dict(site_var=site_var, near=near_tree, vals=vals, btn=btn, adopted=adopted_var,
                                   table=tree, manual=manual)

    # ── 격자점 고르기 ──

    def _current_grid_point(self):
        """(격자점, 거리 km, 가까운 목록) — 설치위치가 없으면 None."""
        site = self.project.site()
        if not site:
            return None
        near = g.nearest_points(*site, n=5)
        if not self._grid_sel or self._grid_sel[0] != site:
            self._grid_sel = (site, near[0][0]["id"])
        for p, km in near:
            if p["id"] == self._grid_sel[1]:
                return p, km, near
        return near[0][0], near[0][1], near

    def _on_grid_pick(self, tree):
        sel = tree.selection()
        site = self.project.site()
        if not sel or not site or (self._grid_sel and self._grid_sel[1] == sel[0]):
            return
        self._grid_sel = (site, sel[0])
        self.refresh_grid_tabs()
        self.set_status(f"격자점을 {sel[0]}(으)로 바꿨습니다.")

    # ── 화면 갱신 ──

    def refresh_grid_tabs(self):
        cur = self._current_grid_point()
        for kind, ui in self._grid_ui.items():
            ui["site_var"].set(site_text(self.project.site()))
            ui["near"].delete(*ui["near"].get_children())
            ui["table"].delete(*ui["table"].get_children())
            if not cur:
                for v in ui["vals"].values():
                    v.set("-")
                ui["btn"].configure(state="disabled")
            else:
                point, _, near = cur
                for p, km in near:
                    ui["near"].insert("", "end", iid=p["id"], values=(p["id"], f'{p["lat"]:.3f}, {p["lon"]:.3f}', f"{km:.1f}"))
                ui["near"].selection_set(point["id"])
                ui["btn"].configure(state="normal")
                (self._fill_wave if kind == "wave" else self._fill_wind)(ui, point)
            ui["manual"].refresh(self.project)
        self._show_grid_adopted()

    def _fill_wave(self, ui, point):
        s = g.wave_summary(point)
        ui["vals"]["hs50"].set(f"{fmt(s['hs_50yr'], 1)} m")
        ui["vals"]["tp50"].set(f"{fmt(s['tp_50yr'], 1)} s")
        ui["vals"]["dir50"].set(s["dir_50yr"] or "-")
        ui["vals"]["hs1"].set(f"{fmt(s['hs_1yr'])} m  ({s['dir_1yr']})")
        ui["vals"]["tp1"].set(f"{fmt(s['tp_1yr'])} s")
        t = s["table"]
        for d in g.directions():
            row = [d, f"{fmt(t['hs_1yr_est'][d])} / {fmt(t['tp_1yr_est'][d])}"]
            row += [f"{t['hs'][rp][d]} / {t['tp'][rp][d]}" for rp in t["hs"]]
            row.append(t["cause"]["50"][d])
            ui["table"].insert("", "end", values=row, tags=("gov",) if d == s["dir_50yr"] else ())

    def _fill_wind(self, ui, point):
        s = g.wind_summary(point)
        ui["vals"]["u50"].set(f"{fmt(s['u_50yr'], 1)} m/s")
        ui["vals"]["dir50"].set(s["dir_50yr"] or "-")
        ui["vals"]["u1"].set(f"{fmt(s['u_1yr'])} m/s  ({s['dir_1yr']})")
        t = s["table"]
        for d in g.directions():
            row = [d, fmt(t["speed_1yr_est"][d])] + [t["speed"][rp][d] for rp in t["speed"]]
            ui["table"].insert("", "end", values=row, tags=("gov",) if d == s["dir_50yr"] else ())

    def _show_grid_adopted(self):
        if "wave" in self._grid_ui:
            hs = self.project.get("deepwave_hs_50yr")
            self._grid_ui["wave"]["adopted"].set(
                f"반영됨: Hs {hs['value']} m / Tp {self.project.value('deepwave_tp_50yr')} s "
                f"({self.project.value('deepwave_dir_50yr') or '-'})" if hs else "")
        if "wind" in self._grid_ui:
            u = self.project.get("wind_speed_50yr")
            self._grid_ui["wind"]["adopted"].set(
                f"반영됨: {u['value']} m/s ({self.project.value('wind_dir_50yr') or '-'})" if u else "")

    # ── 반영 ──

    def _grid_basis(self, point, km):
        return f"격자점 {point['id']} ({point['lat']:.3f}, {point['lon']:.3f}), 설치위치에서 {km:.1f} km"

    def _on_wave_adopt(self):
        point, km, _ = self._current_grid_point()
        site = self.project.site()
        s = g.wave_summary(point)
        base = self._grid_basis(point, km)

        def rec(key, v, basis):
            return make_record(key, v, g.SOURCE_NAME, basis, ref=g.source_files(), site=site)

        self.project.set_many({
            "deepwave_hs_50yr": rec("deepwave_hs_50yr", s["hs_50yr"], f"{base}, 50년 16방위 중 최댓값({s['dir_50yr']})"),
            "deepwave_tp_50yr": rec("deepwave_tp_50yr", s["tp_50yr"], f"{base}, 50년 최대 파고 방향({s['dir_50yr']})의 주기"),
            "deepwave_dir_50yr": rec("deepwave_dir_50yr", s["dir_50yr"], base),
            "deepwave_hs_1yr": rec("deepwave_hs_1yr", s["hs_1yr"], f"{base}, {g.ONE_YR_BASIS}, 최대 방향({s['dir_1yr']})"),
            "deepwave_tp_1yr": rec("deepwave_tp_1yr", s["tp_1yr"], f"{base}, 방향({s['dir_1yr']})의 Hs-Tp 직선회귀로 추정"),
            "deepwave_table": rec("deepwave_table", s["table"], base),
        })
        self.set_status(f"심해설계파 값을 반영했습니다 (격자점 {point['id']}).")

    def _on_wind_adopt(self):
        point, km, _ = self._current_grid_point()
        site = self.project.site()
        s = g.wind_summary(point)
        base = self._grid_basis(point, km) + ", 해수면 위 10 m 풍속(U10)"

        def rec(key, v, basis):
            return make_record(key, v, g.SOURCE_NAME, basis, ref=g.source_files(), site=site)

        self.project.set_many({
            "wind_speed_50yr": rec("wind_speed_50yr", s["u_50yr"], f"{base}, 50년 16방위 중 최댓값({s['dir_50yr']})"),
            "wind_dir_50yr": rec("wind_dir_50yr", s["dir_50yr"], base),
            "wind_speed_1yr": rec("wind_speed_1yr", s["u_1yr"], f"{base}, {g.ONE_YR_BASIS}, 최대 방향({s['dir_1yr']})"),
            "wind_table": rec("wind_table", s["table"], base),
        })
        self.set_status(f"해상풍 값을 반영했습니다 (격자점 {point['id']}).")

    # ── 직접 입력 ──

    def _grid_manual_adopt(self, kind, pairs, drop):
        """pairs: [(50년 키, 1년 키, 이름)] — 1년 ≤ 50년 확인. drop: 직접 입력과 섞이면 안 되는 격자 기록(방향별 표 등)."""
        card = self._grid_ui[kind]["manual"]
        vals, errs = card.parse()
        errs += [f"{k}: 0보다 커야 합니다" for k, v in vals.items() if isinstance(v, float) and v <= 0]
        if not errs:
            errs += [f"1년 {n}이 50년보다 큽니다" for k50, k1, n in pairs if vals[k1] > vals[k50]]
        if errs:
            messagebox.showerror("입력 확인", "\n".join(errs))
            return None
        self.project.drop(*[k for k in drop if k not in vals])
        self.project.set_many(card.records(self.project, vals))
        return vals

    def _on_wave_manual(self):
        vals = self._grid_manual_adopt("wave", [("deepwave_hs_50yr", "deepwave_hs_1yr", "Hs")],
                                       ("deepwave_table", "deepwave_dir_50yr"))
        if vals:
            self.set_status(f"심해설계파를 직접 입력값으로 반영했습니다 — 50년 Hs {vals['deepwave_hs_50yr']:g} m.")

    def _on_wind_manual(self):
        vals = self._grid_manual_adopt("wind", [("wind_speed_50yr", "wind_speed_1yr", "풍속")], ("wind_table", "wind_dir_50yr"))
        if vals:
            self.set_status(f"해상풍을 직접 입력값으로 반영했습니다 — 50년 {vals['wind_speed_50yr']:g} m/s.")
