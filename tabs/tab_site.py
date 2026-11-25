"""1 설치위치 — 화면 안 지도(OpenStreetMap) 클릭 또는 좌표 입력(DD / DMS / DM / UTM)으로 설치위치를 정합니다.

여기서 정한 좌표(site_lat, site_lon)가 다른 모든 탭의 기준이 됩니다.
지도는 Edge 창을 화면 밖에 띄운 뒤 왼쪽 지도 칸 안에 끼워 넣어 보여 줍니다(embed_win).
"""
import queue
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from constants import ACCENT, ACCENT_T, SURF, SURF2, LABEL, TEXT, F_LABEL, F_LABEL_B
from widgets import section_label, field_label, field_entry, primary_button, secondary_button, card_frame

import app_paths
import coord
import embed_win
from map_bridge import MapBridge, MapBridgeError, WINDOW_TITLE
from tabs.common import note_label

_FORMATS = {
    "DD": ("십진법 (DD)", [("위도 (°N)", ["예: 35.000000"]), ("경도 (°E)", ["예: 126.000000"])]),
    "DMS": ("도분초 (DMS)", [("위도 (N) — 도 / 분 / 초", ["도", "분", "초"]),
                           ("경도 (E) — 도 / 분 / 초", ["도", "분", "초"])]),
    "DM": ("도분 (DM)", [("위도 (N) — 도 / 분(소수)", ["도", "분"]),
                       ("경도 (E) — 도 / 분(소수)", ["도", "분"])]),
    "UTM": ("UTM", [("Easting / Northing (m)", ["Easting", "Northing"])]),
}
_LABEL_TO_KEY = {v[0]: k for k, v in _FORMATS.items()}
MAP_SOURCE = "지도 클릭 (OpenStreetMap)"

_POLL_MS = 200
_FIND_MS = 100
_FIND_TIMEOUT_MS = 20000


class SiteTabMixin:
    def _build_site_tab(self, parent):
        self.map_bridge = MapBridge(app_paths.WEB_DIR, app_paths.map_profile_dir(),
                                    user_agent=f"KOMPAS/{self.app_version} (+{self.app_url})")
        self._map_hwnd = None
        self._map_margins = None

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_site_map_card(body).grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = ctk.CTkScrollableFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        self._build_site_input_card(right).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._build_site_current_card(right).grid(row=1, column=0, sticky="ew")

        self.after(_POLL_MS, self._poll_map_inbox)
        self.after(300, self._start_embedded_map)

    # ── 화면 안 지도 ──

    def _build_site_map_card(self, parent):
        card = card_frame(parent)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 2))
        section_label(head, "지도에서 설치위치 클릭").pack(side="left")
        secondary_button(head, "지도 다시 불러오기", self._reload_embedded_map, width=130).pack(side="right")
        note_label(card, "지도를 클릭하면 설치위치로 바로 반영됩니다. 휠로 확대 · 축소합니다.").pack(anchor="w", padx=14, pady=(0, 6))

        self._map_holder = tk.Frame(card, bg=SURF, highlightthickness=0, bd=0)
        self._map_holder.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._map_holder.bind("<Configure>", self._on_map_holder_resize)
        self._map_msg = ctk.CTkLabel(self._map_holder, text="지도 불러오는 중...", font=F_LABEL, text_color=LABEL,
                                     fg_color=SURF, wraplength=520)
        self._map_msg.place(relx=0.5, rely=0.5, anchor="center")
        return card

    def _start_embedded_map(self, force=False):
        self._map_msg.configure(text="지도 불러오는 중...")
        self._map_msg.place(relx=0.5, rely=0.5, anchor="center")
        try:
            self.map_bridge.open_window(force=force)
        except MapBridgeError as e:
            self._map_msg.configure(text=str(e))
            return
        self._map_find_elapsed = 0
        self.after(_FIND_MS, self._try_embed_map)

    def _try_embed_map(self):
        hwnd = embed_win.find_window(WINDOW_TITLE)
        if hwnd:
            self.update_idletasks()
            h = self._map_holder
            embed_win.embed(hwnd, h.winfo_id(), h.winfo_width(), h.winfo_height())
            self._map_hwnd = hwnd
            self._map_margins = None
            self._map_find_elapsed = 0
            self.after(_FIND_MS, self._fit_embedded_map)
            return
        self._map_find_elapsed += _FIND_MS
        if self._map_find_elapsed < _FIND_TIMEOUT_MS:
            self.after(_FIND_MS, self._try_embed_map)
        else:
            self._map_msg.configure(text="지도를 불러오지 못했습니다 — 오른쪽 위 '지도 다시 불러오기'를 눌러 주세요.")

    def _fit_embedded_map(self):
        """Edge 제목표시줄이 지도 칸 밖으로 잘려 나가도록 창 위치를 맞추고, 그 뒤에 지도를 보여 줍니다."""
        if not embed_win.is_alive(self._map_hwnd):
            return
        margins = embed_win.frame_margins(self._map_hwnd)
        if margins is None and self._map_find_elapsed < _FIND_TIMEOUT_MS:
            self._map_find_elapsed += _FIND_MS
            self.after(_FIND_MS, self._fit_embedded_map)
            return
        self._map_margins = margins
        h = self._map_holder
        embed_win.resize(self._map_hwnd, h.winfo_width(), h.winfo_height(), margins)
        self._map_msg.place_forget()

    def _on_map_holder_resize(self, event):
        if embed_win.is_alive(self._map_hwnd):
            embed_win.resize(self._map_hwnd, event.width, event.height, self._map_margins)

    def _reload_embedded_map(self):
        embed_win.close(self._map_hwnd)
        self._map_hwnd = None
        self.after(800, lambda: self._start_embedded_map(force=True))

    def close_embedded_map(self):
        if not hasattr(self, "map_bridge"):
            return
        closed = embed_win.is_alive(self._map_hwnd)
        embed_win.close(self._map_hwnd)
        self.map_bridge.close(wait_for_page=not closed)

    def _poll_map_inbox(self):
        latest = None
        try:
            while True:
                latest = self.map_bridge.inbox.get_nowait()
        except queue.Empty:
            pass
        if latest:
            self._apply_site(*latest, MAP_SOURCE, "지도(OpenStreetMap)에서 클릭한 위치")
        self.after(_POLL_MS, self._poll_map_inbox)

    # ── 좌표 입력 ──

    def _build_site_input_card(self, parent):
        card = card_frame(parent)
        section_label(card, "좌표 입력").pack(anchor="w", padx=14, pady=(12, 6))
        field_label(card, "좌표 형식").pack(anchor="w", padx=14, pady=(0, 2))
        self._site_fmt_var = ctk.StringVar(value=_FORMATS["DD"][0])
        ctk.CTkOptionMenu(card, variable=self._site_fmt_var, values=[v[0] for v in _FORMATS.values()],
                          command=self._on_site_fmt_change, fg_color=SURF2).pack(fill="x", padx=14, pady=(0, 10))

        area = ctk.CTkFrame(card, fg_color="transparent")
        area.pack(fill="x", padx=14)
        self._site_fmt_frames, self._site_vars = {}, {}
        for key, (_, rows) in _FORMATS.items():
            frame = ctk.CTkFrame(area, fg_color="transparent")
            if key == "UTM":
                field_label(frame, "구역 (동경 126° 서쪽 51N, 동쪽 52N)").pack(anchor="w")
                self._site_utm_zone = ctk.StringVar(value="52N")
                ctk.CTkSegmentedButton(frame, variable=self._site_utm_zone, values=["51N", "52N"], fg_color=SURF2,
                                       selected_color=ACCENT, selected_hover_color=ACCENT_T).pack(fill="x", pady=(0, 8))
            vars_ = []
            for row_label, placeholders in rows:
                field_label(frame, row_label).pack(anchor="w")
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=(0, 8))
                for ph in placeholders:
                    v = ctk.StringVar()
                    field_entry(row, v, ph).pack(side="left", fill="x", expand=True, padx=2)
                    vars_.append(v)
            self._site_vars[key] = vars_
            self._site_fmt_frames[key] = frame
        self._site_fmt_frames["DD"].pack(fill="x")
        primary_button(card, "이 좌표로 설치위치 설정", self._on_site_manual_apply, width=0).pack(fill="x", padx=14, pady=(4, 14))
        return card

    def _on_site_fmt_change(self, label):
        key = _LABEL_TO_KEY[label]
        for k, f in self._site_fmt_frames.items():
            (f.pack(fill="x") if k == key else f.pack_forget())

    def _read_site_manual(self):
        key = _LABEL_TO_KEY[self._site_fmt_var.get()]
        raw = [s.get().strip() for s in self._site_vars[key]]
        v = [float(x) for x in raw]
        if key == "DD":
            lat, lon = v
        elif key == "DMS":
            lat, lon = coord.dms_to_dd(*v[:3]), coord.dms_to_dd(*v[3:])
        elif key == "DM":
            lat, lon = coord.dm_to_dd(*v[:2]), coord.dm_to_dd(*v[2:])
        else:
            zone, hemi = coord.parse_utm_zone(self._site_utm_zone.get())
            lat, lon = coord.utm_to_dd(zone, hemi, v[0], v[1])
            raw = [self._site_utm_zone.get()] + raw
            return lat, lon, coord.UTM_SOURCE, "입력값: " + " / ".join(raw)
        return lat, lon, f"좌표 입력 ({key})", "입력값: " + " / ".join(raw)

    def _on_site_manual_apply(self):
        try:
            lat, lon, source, basis = self._read_site_manual()
        except (ValueError, IndexError):
            self.set_status("좌표를 고른 형식에 맞게 숫자로 넣어 주세요.")
            return
        self._apply_site(lat, lon, source, basis)

    def _apply_site(self, lat, lon, source, basis):
        if not coord.in_korea_waters(lat, lon):
            if not messagebox.askyesno("좌표 확인", f"({lat:.4f}, {lon:.4f})는 우리나라 주변 해역 범위를 벗어났습니다.\n"
                                                 "이 프로그램의 자료는 우리나라 해역만 있습니다. 그래도 설정할까요?"):
                return
        removed = self.project.set_site(round(lat, 6), round(lon, 6), source, basis)
        msg = f"설치위치를 설정했습니다 ({source})."
        if removed:
            msg += f" 이전 좌표로 구한 값 {removed}개는 지웠습니다 — 각 탭에서 다시 반영해 주세요."
        self.set_status(msg)

    # ── 지금 설치위치 ──

    def _build_site_current_card(self, parent):
        card = card_frame(parent)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 6))
        section_label(head, "지금 설치위치").pack(side="left")
        secondary_button(head, "입력칸에 채우기", self._on_site_fill_inputs, width=120).pack(side="right")
        self._site_disp = {}
        for key, label in [("DD", "십진법"), ("DMS", "도분초"), ("DM", "도분"), ("UTM", "UTM")]:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row, text=label, font=F_LABEL, text_color=LABEL, width=70, anchor="w").pack(side="left")
            var = ctk.StringVar(value="-")
            ctk.CTkLabel(row, textvariable=var, font=F_LABEL_B, text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            self._site_disp[key] = var
        self._site_utm_note_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._site_utm_note_var, font=F_LABEL, text_color=LABEL, anchor="w",
                     justify="left", wraplength=470).pack(fill="x", padx=14, pady=(2, 0))
        self._site_source_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, textvariable=self._site_source_var, font=F_LABEL, text_color=LABEL, anchor="w",
                     justify="left", wraplength=470).pack(fill="x", padx=14, pady=(6, 14))
        return card

    def _on_site_fill_inputs(self):
        """지금 설치위치를 좌표 입력 칸(네 가지 형식 모두)에 채워 넣습니다."""
        site = self.project.site()
        if not site:
            self.set_status("아직 설치위치가 없습니다 — 지도를 클릭하거나 좌표를 넣어 주세요.")
            return
        lat, lon = site
        la_d, la_m, la_s = coord.dd_to_dms(lat)
        lo_d, lo_m, lo_s = coord.dd_to_dms(lon)
        la_dm_d, la_dm_m = coord.dd_to_dm(lat)
        lo_dm_d, lo_dm_m = coord.dd_to_dm(lon)
        zone, hemi, e, n = coord.dd_to_utm(lat, lon, self._site_utm_zone_in_use())
        values = {"DD": [f"{lat:.6f}", f"{lon:.6f}"],
                  "DMS": [str(la_d), str(la_m), f"{la_s:.2f}", str(lo_d), str(lo_m), f"{lo_s:.2f}"],
                  "DM": [str(la_dm_d), f"{la_dm_m:.4f}", str(lo_dm_d), f"{lo_dm_m:.4f}"],
                  "UTM": [str(e), str(n)]}
        for key, vals in values.items():
            for var, v in zip(self._site_vars[key], vals):
                var.set(v)
        self._site_utm_zone.set(f"{zone}{hemi}")
        self.set_status("지금 설치위치를 좌표 입력 칸에 채웠습니다 (네 가지 형식 모두).")

    def _site_utm_zone_in_use(self):
        """UTM으로 입력한 설치위치면 그때 고른 구역(예: 52), 아니면 None(경도로 정한 정식 구역)."""
        rec = self.project.get("site_lat")
        return coord.entered_utm_zone(rec.get("source"), rec.get("basis")) if rec else None

    def refresh_site_tab(self):
        site = self.project.site()
        self.map_bridge.site = list(site) if site else None
        if not site:
            for v in self._site_disp.values():
                v.set("-")
            self._site_utm_note_var.set("")
            self._site_source_var.set("")
            return
        zone = self._site_utm_zone_in_use()
        for k, text in coord.format_all(*site, utm_zone=zone).items():
            self._site_disp[k].set(text)
        self._site_utm_note_var.set(coord.utm_note(*site, zone))
        rec = self.project.get("site_lat")
        self._site_source_var.set(f"정한 방법: {rec['source']}   {rec['basis']}")
