"""표(Treeview) 등 기본 tkinter(ttk) 부품을 어두운 화면 색에 맞추는 설정 — 프로그램 시작 때 한 번 부름."""
from tkinter import ttk

from constants import BG, SURF, SURF2, BORDER, TEXT, TEXT_DIM, SELECT_ROW, F_TBL, F_TBL_H, F_LABEL


def init_dark_style(root):
    for widget in ("Entry", "Text", "Listbox"):
        root.option_add(f"*{widget}.background", SURF2)
        root.option_add(f"*{widget}.foreground", TEXT)
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure(".", background=BG, foreground=TEXT, fieldbackground=SURF2, bordercolor=BORDER,
                lightcolor=BORDER, darkcolor=BORDER, troughcolor=SURF, font=F_LABEL)
    s.map(".", background=[("disabled", BG)], foreground=[("disabled", TEXT_DIM)])
    for name in ("Treeview", "Dark.Treeview"):
        s.configure(name, background=SURF2, foreground=TEXT, fieldbackground=SURF2, rowheight=24, font=F_TBL,
                    borderwidth=0)
        s.configure(f"{name}.Heading", background=SURF, foreground=TEXT, font=F_TBL_H, relief="flat")
        s.map(name, background=[("selected", SELECT_ROW)], foreground=[("selected", TEXT)])
        s.map(f"{name}.Heading", background=[("active", SURF2)])
    s.configure("Vertical.TScrollbar", background=SURF2, troughcolor=SURF, bordercolor=SURF, arrowcolor=TEXT_DIM)
