"""화면 부품 — 제목 · 입력창 · 버튼 · 카드 · 상태 표시줄."""
import tkinter as tk

import customtkinter as ctk
from constants import ACCENT, ACCENT_T, SURF, SURF2, BORDER, TEXT, TEXT_DIM, LABEL, BG, F_SECTION, F_LABEL, F_ENTRY, F_BTN


def _safe_scroll_wheel():
    """스크롤 칸(CTkScrollableFrame) 위의 펼침 목록에서 마우스 휠을 굴릴 때 나던 오류를 막음
    (그때는 event.widget이 위젯이 아니라 이름 글자로 옴 — 그런 곳에서는 스크롤 칸을 움직이지 않음)"""
    cls = ctk.CTkScrollableFrame
    if getattr(cls, "_safe_wheel", False):
        return
    original = cls.check_if_master_is_canvas

    def check(self, widget):
        if isinstance(widget, str):
            try:
                widget = self.nametowidget(widget)
            except (KeyError, tk.TclError):
                return False
        return original(self, widget)
    cls.check_if_master_is_canvas = check
    cls._safe_wheel = True


_safe_scroll_wheel()


def section_label(parent, text):
    """섹션 제목 (강조색, 굵게)"""
    return ctk.CTkLabel(parent, text=text, text_color=ACCENT, font=F_SECTION, anchor="w")


def field_label(parent, text):
    """입력창 위 라벨"""
    return ctk.CTkLabel(parent, text=text, text_color=LABEL, font=F_LABEL, anchor="w")


def field_entry(parent, var, placeholder="", show=None):
    """입력창 (show='•'이면 글자를 가림 — 인증키 등)"""
    kw = {"show": show} if show else {}
    return ctk.CTkEntry(parent, textvariable=var, placeholder_text=placeholder, fg_color=SURF2, border_color=BORDER,
                        text_color=TEXT, placeholder_text_color=TEXT_DIM, corner_radius=6, font=F_ENTRY, **kw)


def primary_button(parent, text, command, width=110):
    """주요 동작 버튼"""
    return ctk.CTkButton(parent, text=text, command=command, width=width, font=F_BTN,
                         fg_color=ACCENT, hover_color=ACCENT_T, text_color=BG)


def secondary_button(parent, text, command, width=110):
    """보조 동작 버튼"""
    return ctk.CTkButton(parent, text=text, command=command, width=width, font=F_LABEL,
                         fg_color=SURF, hover_color=BORDER, text_color=TEXT, border_width=1, border_color=BORDER)


def status_bar(parent, textvariable):
    """맨 아래 상태 표시줄"""
    return ctk.CTkLabel(parent, textvariable=textvariable, anchor="w", text_color=LABEL, font=F_LABEL,
                        fg_color=SURF, corner_radius=6)


def card_frame(parent):
    """카드형 패널 (둥근 모서리 + 테두리)"""
    return ctk.CTkFrame(parent, fg_color=SURF2, corner_radius=10, border_width=1, border_color=BORDER)


def enable_tab_contrast(tabview):
    """선택된 탭 글자를 어두운 색으로 바꿔 강조색 배경 위에서도 잘 보이게 (탭을 다 추가한 뒤 한 번 부름)"""
    sb = tabview._segmented_button

    def _refresh():
        current = sb.get()
        for name, btn in sb._buttons_dict.items():
            btn.configure(text_color=BG if name == current else TEXT)

    existing_command = tabview._command

    def _combined_command():
        if existing_command:
            existing_command()
        _refresh()

    tabview.configure(command=_combined_command)
    _refresh()
