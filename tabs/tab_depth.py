"""3 수심 — 설치위치 주변의 국립해양조사원 수심 측정점을 찾아 수심을 정합니다 (인증키가 있을 때), 또는 직접 입력.

API 수심은 평균해면(MSL) 기준이라 조위관측소 평균해면 높이를 빼서 D.L. 기준으로 바꿉니다(v0.2, source_depth 참고).
2 설계조위를 먼저 반영했으면 그 MSL(같은 관측소)을, 아니면 가장 가까운 관측소 값을 씁니다.
"""
import threading
from tkinter import messagebox

import customtkinter as ctk

from constants import ACCENT, TEXT, SURF2, BORDER, F_LABEL, F_LABEL_B, WARN
from widgets import section_label, primary_button, secondary_button, field_entry, card_frame

import files
import settings
import source_depth as kd
from schema import make_record
from tabs.common import banner, site_text, note_label, kv_row, make_tree, fmt
from tabs.manual_input import ManualCard


class DepthTabMixin:
    def _build_depth_tab(self, parent):
        self._depth_site_var = ctk.StringVar()
        banner(parent, self._depth_site_var)

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color=SURF2, corner_radius=10, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        section_label(left, "공공데이터포털 인증키").pack(anchor="w", padx=14, pady=(12, 2))
        note_label(left, f"{kd.API_GUIDE}. 이 컴퓨터에만 저장됩니다.").pack(anchor="w", padx=14, pady=(0, 4))
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        self._depth_key_var = ctk.StringVar(value=settings.data_key())
        field_entry(row, self._depth_key_var, "인증키 (Decoding 키)", show="•").pack(side="left", fill="x", expand=True)
        secondary_button(row, "저장", self._on_depth_key_save, width=70).pack(side="left", padx=(6, 0))

        section_label(left, "측정점으로 수심 찾기").pack(anchor="w", padx=14, pady=(6, 6))
        self._depth_btn = primary_button(left, "설치위치 주변 수심 측정점 찾기", self._on_depth_query, width=0)
        self._depth_btn.pack(fill="x", padx=14, pady=(0, 10))
        self._depth_info = {k: ctk.StringVar(value="-") for k in ("range", "count", "nearest", "datum")}
        kv_row(left, "찾은 범위", self._depth_info["range"])
        kv_row(left, "측정점", self._depth_info["count"])
        kv_row(left, "가장 가까운 측정점", self._depth_info["nearest"])
        kv_row(left, "D.L. 환산 (− MSL)", self._depth_info["datum"])

        section_label(left, "수심 정하는 방법").pack(anchor="w", padx=14, pady=(14, 4))
        self._depth_method = ctk.StringVar(value=kd.DEFAULT_METHOD)
        self._depth_radio = {}
        for key, label in kd.METHODS.items():
            rb = ctk.CTkRadioButton(left, text=label, variable=self._depth_method, value=key, font=F_LABEL,
                                    text_color=TEXT, fg_color=ACCENT)
            rb.pack(anchor="w", padx=18, pady=3)
            self._depth_radio[key] = rb
        self._depth_adopt_btn = primary_button(left, "이 값을 수심으로 반영", self._on_depth_adopt, width=0)
        self._depth_adopt_btn.pack(fill="x", padx=14, pady=(12, 6))
        self._depth_adopt_btn.configure(state="disabled")
        self._depth_adopted_var = ctk.StringVar(value="")
        ctk.CTkLabel(left, textvariable=self._depth_adopted_var, font=F_LABEL_B, text_color=ACCENT, anchor="w",
                     justify="left", wraplength=560).pack(fill="x", padx=14, pady=(0, 6))
        self._depth_warn_var = ctk.StringVar(value="")
        ctk.CTkLabel(left, textvariable=self._depth_warn_var, font=F_LABEL, text_color=WARN, anchor="w",
                     justify="left", wraplength=560).pack(fill="x", padx=14, pady=(0, 6))
        note_label(left, f"출처: {kd.SOURCE_NAME}").pack(anchor="w", padx=14, pady=(6, 2))
        note_label(left, kd.DATUM_NOTE).pack(anchor="w", padx=14, pady=(0, 12))

        self._depth_manual = ManualCard(left, "직접 입력", [("water_depth", "수심 (D.L. 기준, 양수)", True, None)],
                                        self._on_depth_manual)

        right = card_frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        section_label(right, "가까운 측정점 (최대 15개)").pack(anchor="w", padx=14, pady=(12, 6))
        self._depth_tree = make_tree(right, [("rank", "순위", 50), ("lat", "위도", 100), ("lon", "경도", 100),
                                             ("api", "API (MSL 기준)", 105), ("depth", "D.L. 환산", 85),
                                             ("dist", "거리 (m)", 75)], height=15)
        self._depth_tree.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._depth_result = None

    def _on_depth_key_save(self):
        try:
            settings.set_data_key(self._depth_key_var.get())
        except (OSError, UnicodeEncodeError) as e:
            messagebox.showerror("저장하지 못했습니다", files.why(e))
            return
        self.set_status("인증키를 이 컴퓨터에 저장했습니다." if self._depth_key_var.get().strip() else "인증키를 지웠습니다.")
        self.refresh_depth_tab()

    def _on_depth_query(self):
        site = self.project.site()
        if not site:
            self.set_status("먼저 1 설치위치 탭에서 좌표를 정해 주세요.")
            return
        key = self._depth_key_var.get().strip()
        if not key:
            self.set_status("인증키를 넣어야 측정점을 찾을 수 있습니다 — 없으면 아래 '직접 입력'에 수심을 넣어 주세요.")
            return
        self._depth_btn.configure(state="disabled", text="찾는 중...")
        self.set_status("국립해양조사원 수심 측정점을 찾는 중...")
        msl, note = self._depth_msl_choice(site)
        threading.Thread(target=self._depth_worker, args=(key, site, msl, note), daemon=True).start()

    def _depth_msl_choice(self, site):
        """뺄 MSL — 2 설계조위에서 같은 좌표로 반영한 MSL이 있으면 그것(관측소 일치), 없으면 가장 가까운 관측소."""
        rec = self.project.get("tide_msl")
        if rec and rec.get("value") is not None and rec.get("site") in (None, list(site), tuple(site)):
            return rec["value"], f"2 설계조위에서 반영한 MSL — {rec.get('basis', '')}".rstrip(" —")
        return kd.default_msl(*site)

    def _depth_worker(self, key, site, msl, note):
        try:
            result = kd.estimate(key, *site, msl=msl, msl_note=note)
        except Exception as e:
            self.after(0, self._depth_failed, str(e))
        else:
            self.after(0, self._depth_done, result)

    def _depth_failed(self, message):
        self._depth_btn.configure(state="normal", text="설치위치 주변 수심 측정점 찾기")
        self.set_status(f"수심 측정점을 찾지 못했습니다: {message}")

    def _depth_done(self, result):
        self._depth_btn.configure(state="normal", text="설치위치 주변 수심 측정점 찾기")
        if self.project.site() != (result.lat, result.lon):
            self.set_status("찾는 동안 설치위치가 바뀌어 결과를 버렸습니다. 다시 찾아 주세요.")
            return
        self._depth_result = result
        self._show_depth_result()
        self.set_status(f"수심 측정점 {len(result.ranked)}개를 찾았습니다.")

    def _show_depth_result(self):
        r = self._depth_result
        self._depth_info["range"].set(f"설치위치 ±{r.half_deg:g}° (약 ±{r.half_deg * 111:.1f} km)")
        self._depth_info["count"].set(f"{len(r.ranked)}개")
        self._depth_info["nearest"].set(f"{r.ranked[0][0]:.0f} m")
        self._depth_info["datum"].set(f"MSL {r.msl:.3f} m ({r.msl_note})")
        for key, label in kd.METHODS.items():
            self._depth_radio[key].configure(
                text=f"{label}   →   D.L. {r.methods[key]:.2f} m   (API {r.methods_msl[key]:.2f})")
        self._depth_tree.delete(*self._depth_tree.get_children())
        for i, (dist, (lat, lon, depth)) in enumerate(r.ranked[:15], 1):
            self._depth_tree.insert("", "end", values=(i, f"{lat:.5f}", f"{lon:.5f}", f"{depth:.2f}",
                                                       f"{depth - r.msl:.2f}", f"{dist:.0f}"))
        self._depth_adopt_btn.configure(state="normal")

    def _on_depth_adopt(self):
        r = self._depth_result
        method = self._depth_method.get()
        if r.methods[method] <= 0:
            messagebox.showerror("수심 확인", f"D.L. 기준 수심이 {r.methods[method]:.2f} m (0 이하)입니다 — "
                                 "썰물 때 드러나는 곳입니다. 측량값을 직접 입력해 주세요.")
            return
        rec = make_record("water_depth", round(r.methods[method], 2), kd.SOURCE_NAME,
                          basis=r.basis(method), ref=kd.BASE_URL, site=(r.lat, r.lon))
        rec["msl_used"] = round(r.msl, 3)          # 2 설계조위 MSL과 다른지 확인용
        self.project.set("water_depth", rec)
        self.set_status(f"수심 D.L. {rec['value']} m를 반영했습니다 (API {r.methods_msl[method]:.2f} − MSL {r.msl:.3f}).")

    def _depth_datum_warning(self):
        """반영된 API 수심이 v0.1 방식(MSL 안 뺌)이거나 2 설계조위 MSL과 다른 MSL로 바꿨으면 알림."""
        rec = self.project.get("water_depth")
        if not rec or rec.get("source") != kd.SOURCE_NAME:
            return ""
        if "msl_used" not in rec:
            return ("⚠ v0.1에서 반영한 수심입니다 — API 값(평균해면 기준)을 그대로 써서 평균해면 높이만큼 깊게 잡혔습니다. "
                    "다시 찾아 반영해 주세요(D.L. 환산).")
        tide = self.project.get("tide_msl")
        if tide and tide.get("value") is not None and abs(tide["value"] - rec["msl_used"]) > 0.005:
            return (f"⚠ 수심 환산에 쓴 MSL {rec['msl_used']:.3f} m가 2 설계조위의 MSL {tide['value']:.3f} m와 다릅니다 "
                    "(관측소가 다름) — 수심을 다시 찾아 반영해 주세요.")
        return ""

    def _on_depth_manual(self):
        vals, errs = self._depth_manual.parse()
        if not errs and vals["water_depth"] <= 0:
            errs.append("수심은 0보다 커야 합니다 (해저면까지 깊이, 양수)")
        if errs:
            messagebox.showerror("입력 확인", "\n".join(errs))
            return
        self.project.set_many(self._depth_manual.records(self.project, vals))
        self.set_status(f"수심 {vals['water_depth']:g} m를 직접 입력값으로 반영했습니다.")

    def refresh_depth_tab(self):
        site = self.project.site()
        self._depth_site_var.set(site_text(site))
        if self._depth_result and site != (self._depth_result.lat, self._depth_result.lon):
            self._depth_result = None
            for key, label in kd.METHODS.items():
                self._depth_radio[key].configure(text=label)
            for v in self._depth_info.values():
                v.set("-")
            self._depth_tree.delete(*self._depth_tree.get_children())
            self._depth_adopt_btn.configure(state="disabled")
        rec = self.project.get("water_depth")
        self._depth_adopted_var.set(f"반영됨 (D.L.): {fmt(rec['value'])} m" if rec else "")
        self._depth_warn_var.set(self._depth_datum_warning())
        self._depth_manual.refresh(self.project)
