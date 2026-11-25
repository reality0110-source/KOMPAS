"""위쪽 메뉴 — 이름 · 저장 · 다른 이름으로 저장 · 불러오기 · 새로 시작 (어느 탭에서든 보임)."""
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from constants import SURF, BORDER, LABEL, TEXT_DIM, F_LABEL
from widgets import field_entry, primary_button, secondary_button

import files
from project import FILE_EXT

FILE_TYPES = [("KOMPAS 파일", f"*{FILE_EXT}")]


class MenuBarMixin:
    def _build_menubar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=SURF, corner_radius=0, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x")

        row = ctk.CTkFrame(bar, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(row, text="이름", font=F_LABEL, text_color=LABEL).pack(side="left", padx=(0, 8))
        self._proj_name_var = ctk.StringVar()
        name = field_entry(row, self._proj_name_var, "예: ○○ 해역 검토")
        name.configure(width=260)
        name.pack(side="left")
        primary_button(row, "저장", self._on_project_save, width=80).pack(side="left", padx=(12, 4))
        secondary_button(row, "다른 이름으로 저장", lambda: self._on_project_save(ask=True), width=130).pack(side="left", padx=4)
        secondary_button(row, "불러오기", self._on_project_load, width=80).pack(side="left", padx=4)
        secondary_button(row, "새로 시작", self._on_project_new, width=90).pack(side="left", padx=4)
        self._proj_path_var = ctk.StringVar(value="저장된 파일 없음")
        ctk.CTkLabel(row, textvariable=self._proj_path_var, font=F_LABEL, text_color=TEXT_DIM, anchor="e").pack(
            side="right", padx=(12, 0))

    def refresh_menubar(self):
        self._proj_name_var.set(self.project.name)
        self._proj_path_var.set(f"파일: {self.project.path}" if self.project.path else "저장된 파일 없음")

    def _start_dir(self):
        return str(Path(self.project.path).parent) if self.project.path else None

    def _on_project_save(self, ask=False):
        self.project.name = self._proj_name_var.get().strip()
        path = self.project.path
        if ask or not path:
            path = filedialog.asksaveasfilename(title="저장", defaultextension=FILE_EXT, filetypes=FILE_TYPES,
                                                initialdir=self._start_dir(),
                                                initialfile=f"{self.project.name or 'KOMPAS'}{FILE_EXT}")
            if not path:
                return
        try:
            self.project.save(path)
        except (OSError, UnicodeEncodeError) as e:
            messagebox.showerror("저장하지 못했습니다", f"{files.why(e)}.\n\n{path}\n\n원래 있던 파일은 그대로입니다.")
            self.set_status(f"저장하지 못했습니다 — {files.why(e)}")
            return
        self.refresh_menubar()
        self.set_status(f"저장했습니다: {Path(path).name}")

    def _on_project_load(self):
        path = filedialog.askopenfilename(title="불러오기", filetypes=FILE_TYPES, initialdir=self._start_dir())
        if not path:
            return
        try:
            unknown = self.project.load(path)
        except Exception as e:
            messagebox.showerror("불러오지 못했습니다", str(e))
            return
        msg = f"불러왔습니다: {Path(path).name}"
        if unknown:
            msg += f"  (모르는 값 {len(unknown)}개는 뺐습니다: {', '.join(unknown)})"
        self.set_status(msg)

    def _on_project_new(self):
        if self.project.values and not messagebox.askyesno(
                "새로 시작", "지금 값들을 모두 지우고 새로 시작할까요?\n(저장하지 않은 내용은 사라집니다)"):
            return
        self.project.clear()
        self.set_status("새로 시작했습니다.")
