# KOMPAS — Korea Offshore Metocean Preliminary Assessment System
# 좌표 하나 → 수심 · 극한설계파고 · 설계풍속 · 설계조위 · 설계유속을 자료 출처와 함께 정리
import sys
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

_HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
for sub in ("ui", "modules", ""):
    sys.path.insert(0, str(_HERE / sub) if sub else str(_HERE))

import customtkinter as ctk  # noqa: E402
from constants import ACCENT, ACCENT_T, BG, SURF, SURF2, TEXT, LABEL, TEXT_DIM, F_HDR, F_HDR_SUB, F_LABEL  # noqa: E402
from widgets import status_bar, enable_tab_contrast  # noqa: E402
from ttk_style import init_dark_style  # noqa: E402

import app_paths  # noqa: E402
from project import Project  # noqa: E402
from tabs.tab_site import SiteTabMixin  # noqa: E402
from tabs.tab_depth import DepthTabMixin  # noqa: E402
from tabs.tab_grid import GridTabsMixin  # noqa: E402
from tabs.tab_tide import TideTabMixin  # noqa: E402
from tabs.tab_current import CurrentTabMixin  # noqa: E402
from tabs.tab_result import ResultTabMixin  # noqa: E402
from tabs.menubar import MenuBarMixin  # noqa: E402

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_NAME = "KOMPAS"
APP_VER = "v0.2"
APP_TITLE = f"{APP_NAME} {APP_VER}"
APP_URL = "https://github.com/reality0110-source/KOMPAS"     # 공식 배포처

TABS = ("1 설치위치", "2 설계조위", "3 수심", "4 극한설계파고", "5 설계풍속", "6 설계유속", "7 결과 정리")   # v0.2: 조위 → 수심


def log_error(text):
    """예상하지 못한 오류를 기록 파일 끝에 덧붙임 (너무 길어지면 앞쪽을 버림). 기록하지 못해도 프로그램은 계속."""
    try:
        path = app_paths.error_log()
        old = path.read_text(encoding="utf-8")[-200_000:] if path.exists() else ""
        path.write_text(f"{old}\n===== {datetime.now():%Y-%m-%d %H:%M:%S}  {APP_TITLE} =====\n{text}", encoding="utf-8")
        return True
    except OSError:
        return False


class App(SiteTabMixin, DepthTabMixin, GridTabsMixin, TideTabMixin, CurrentTabMixin, ResultTabMixin, MenuBarMixin, ctk.CTk):
    app_version = APP_VER
    app_url = APP_URL

    def __init__(self):
        super().__init__()
        self._errors_shown = set()
        init_dark_style(self)
        self.title(APP_TITLE)
        self.geometry("1500x860")
        self.minsize(1200, 680)
        self.configure(fg_color=BG)
        self.after(0, lambda: self.state("zoomed"))

        self.project = Project()
        self._build_header()
        self._build_menubar(self)
        self._build_footer()
        self._build_tabs()
        self.project.subscribe(self.refresh_all)
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def report_callback_exception(self, exc, val, tb):
        """예상하지 못한 오류 — 창 없이 실행되므로(.pyw) 그냥 두면 아무 표시 없이 사라집니다. 기록 파일에 남기고 화면에 알림"""
        brief = f"{exc.__name__}: {val}"
        saved = log_error("".join(traceback.format_exception(exc, val, tb)))
        where = f"자세한 내용은 '{app_paths.error_log()}'에 적어 두었습니다" if saved else "기록 파일에는 적지 못했습니다"
        try:
            self.set_status(f"예상하지 못한 오류가 났습니다 — {brief}")
        except Exception:
            pass
        if brief not in self._errors_shown:
            self._errors_shown.add(brief)
            messagebox.showerror("예상하지 못한 오류", f"예상하지 못한 오류가 났습니다.\n\n{brief}\n\n{where}.")

    def _on_close(self):
        self.close_embedded_map()
        self.destroy()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=SURF, corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=APP_NAME, font=F_HDR, text_color=TEXT).place(x=20, y=8)
        ctk.CTkLabel(hdr, text="좌표 하나 → 수심 · 극한설계파고 · 설계풍속 · 설계조위 · 설계유속 — 값마다 자료 출처",
                     font=F_HDR_SUB, text_color=LABEL).place(x=22, y=38)
        ctk.CTkLabel(hdr, text=APP_VER, font=F_LABEL, text_color=TEXT_DIM).place(relx=1.0, x=-16, y=24, anchor="ne")

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self, fg_color=SURF, segmented_button_fg_color=SURF2,
                                      segmented_button_selected_color=ACCENT, segmented_button_selected_hover_color=ACCENT_T)
        pages = {name: self.tabview.add(name) for name in TABS}
        enable_tab_contrast(self.tabview)
        existing = self.tabview._command

        def _on_tab():
            if existing:
                existing()
            self._ensure_page(self.tabview.get())

        self.tabview.configure(command=_on_tab)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(10, 4))

        # 탭마다 (만드는 함수, 다시 그리는 함수) — 처음 열 때 만들고, 값이 바뀌면 지금 보이는 탭만 다시 그림
        P = lambda frame, build, *args: (lambda: build(frame, *args))   # noqa: E731
        self._pages = {
            "1 설치위치": (P(pages["1 설치위치"], self._build_site_tab), self.refresh_site_tab),
            "2 설계조위": (P(pages["2 설계조위"], self._build_tide_tab), self.refresh_tide_tab),
            "3 수심": (P(pages["3 수심"], self._build_depth_tab), self.refresh_depth_tab),
            "4 극한설계파고": (P(pages["4 극한설계파고"], self._build_grid_tab, "wave"), self.refresh_grid_tabs),
            "5 설계풍속": (P(pages["5 설계풍속"], self._build_grid_tab, "wind"), self.refresh_grid_tabs),
            "6 설계유속": (P(pages["6 설계유속"], self._build_current_tab), self.refresh_current_tab),
            "7 결과 정리": (P(pages["7 결과 정리"], self._build_result_tab), self.refresh_result_tab),
        }
        self._built, self._dirty = set(), set(self._pages)
        self._ensure_page("1 설치위치")   # 지도가 있어 처음부터 만듦

    def _ensure_page(self, name):
        """처음 열면 만들고, 값이 바뀐 뒤 처음 보면 다시 그립니다."""
        build, refresh = self._pages[name]
        if name not in self._built:
            build()
            self._built.add(name)
            self._dirty.add(name)
        if name in self._dirty:
            self._dirty.discard(name)
            refresh()

    def ensure_all_pages(self):
        """모든 탭을 만들고 다시 그림 (시험용)."""
        for name in self._pages:
            self._ensure_page(name)

    def show_tab(self, name):
        self.tabview.set(name)
        self._ensure_page(name)

    def _build_footer(self):
        self.status_var = ctk.StringVar(value="1 설치위치 탭에서 지도를 클릭하거나 좌표를 넣어 시작하세요.")
        status_bar(self, self.status_var).pack(fill="x", side="bottom", padx=14, pady=(0, 8))

    def set_status(self, msg):
        self.status_var.set(msg)

    def refresh_all(self):
        """값이 바뀌면 메뉴와 지금 보이는 탭만 다시 그리고, 나머지 탭은 열 때 그립니다."""
        self._dirty = set(self._pages)
        self.refresh_menubar()
        self._ensure_page(self.tabview.get())


def _already_running():
    """이미 실행 중이면 그 창을 앞으로 불러오고 True."""
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32")
    global _instance_mutex
    _instance_mutex = kernel32.CreateMutexW(None, False, "Local\\KOMPAS_SINGLE_INSTANCE")
    if ctypes.get_last_error() != 183:  # ERROR_ALREADY_EXISTS
        return False
    hwnd = user32.FindWindowW(None, APP_TITLE)
    if hwnd:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    return True


if __name__ == "__main__":
    if not _already_running():
        App().mainloop()
