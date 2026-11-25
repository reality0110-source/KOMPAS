"""여러 탭이 같이 쓰는 작은 화면 조각."""
from tkinter import ttk

import customtkinter as ctk

from constants import SURF2, LABEL, TEXT, WARN, F_LABEL, F_LABEL_B, F_DESC

import coord


def banner(parent, textvariable):
    """탭 맨 위 — 지금 설치위치 표시줄."""
    frame = ctk.CTkFrame(parent, fg_color=SURF2, corner_radius=8)
    frame.pack(fill="x", padx=12, pady=(12, 8))
    ctk.CTkLabel(frame, textvariable=textvariable, font=F_LABEL_B, text_color=TEXT, anchor="w").pack(fill="x", padx=12, pady=8)
    return frame


def site_text(site):
    if not site:
        return "설치위치가 아직 없습니다 — 1 설치위치 탭에서 좌표를 먼저 정해 주세요."
    return f"설치위치:  {coord.format_all(*site)['DD']}"


def note_label(parent, text, warn=False):
    return ctk.CTkLabel(parent, text=text, font=F_DESC, text_color=WARN if warn else LABEL, anchor="w",
                        justify="left", wraplength=620)


def kv_row(parent, label, var, width=150):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=2)
    ctk.CTkLabel(row, text=label, font=F_LABEL, text_color=LABEL, width=width, anchor="w").pack(side="left")
    ctk.CTkLabel(row, textvariable=var, font=F_LABEL_B, text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
    return row


def make_tree(parent, columns, height=8):
    """columns: [(id, 제목, 폭), ...]"""
    tree = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings", style="Dark.Treeview",
                        selectmode="browse", height=height)
    for cid, title, width in columns:
        tree.heading(cid, text=title)
        tree.column(cid, width=width, anchor="center", stretch=True)
    return tree


def fmt(v, digits=2):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def fmt_trim(v, digits=3):
    """소수 digits자리까지, 끝의 0은 뺌 (6.900 → 6.9)"""
    if isinstance(v, float):
        return f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return fmt(v)
