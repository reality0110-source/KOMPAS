"""7 결과 정리 — 반영된 모든 값을 출처 · 근거와 함께 보고, HTML 한 장으로 저장합니다."""
import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from constants import ACCENT, OK_BG, TEXT, F_LABEL, F_LABEL_B
from widgets import section_label, primary_button, card_frame

import files
import report_html
from schema import FIELDS, SECTIONS, TABLE_KEYS
from tabs.common import make_tree, note_label, fmt_trim


class ResultTabMixin:
    def _build_result_tab(self, parent):
        card = card_frame(parent)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 6))
        section_label(head, "반영된 값 · 출처 · 근거").pack(side="left")
        primary_button(head, "HTML로 저장", self._on_save_html, width=130).pack(side="right")
        self._res_count_var = ctk.StringVar(value="")
        ctk.CTkLabel(head, textvariable=self._res_count_var, font=F_LABEL_B, text_color=ACCENT).pack(side="right", padx=12)

        self._res_tree = make_tree(card, [("sec", "항목", 110), ("name", "값 이름", 200), ("value", "값", 90),
                                          ("unit", "단위", 60), ("source", "출처", 380), ("basis", "근거", 480)], height=20)
        for col in ("name", "source", "basis"):
            self._res_tree.column(col, anchor="w")
        self._res_tree.tag_configure("ok", background=OK_BG)
        note_label(card, "행을 누르면 출처 · 근거 전체가 아래에 보입니다. HTML은 브라우저에서 열려 인쇄(PDF 저장)할 수 있습니다."
                   ).pack(side="bottom", anchor="w", padx=14, pady=(0, 12))
        self._res_detail = ctk.CTkTextbox(card, height=90, font=F_LABEL, text_color=TEXT, wrap="word")
        self._res_detail.pack(side="bottom", fill="x", padx=14, pady=(0, 6))
        self._res_tree.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self._res_tree.bind("<<TreeviewSelect>>", self._on_result_select)

    def refresh_result_tab(self):
        self._res_tree.delete(*self._res_tree.get_children())
        for key, f in FIELDS.items():
            rec = self.project.get(key)
            sec = f"{f.section} {SECTIONS[f.section]}"
            if not rec:
                self._res_tree.insert("", "end", iid=key, values=(sec, f.name, "", f.unit, "", ""))
                continue
            value = "(표)" if key in TABLE_KEYS else fmt_trim(rec["value"], 6 if f.section == "1" else 3)
            self._res_tree.insert("", "end", iid=key, tags=("ok",),
                                  values=(sec, f.name, value, f.unit, rec.get("source") or "", rec.get("basis") or ""))
        done, total = report_html.counts(self.project)
        self._res_count_var.set(f"반영 {done}/{total}")

    def _on_result_select(self, event=None):
        sel = self._res_tree.selection()
        self._res_detail.delete("1.0", "end")
        if not sel:
            return
        f, rec = FIELDS[sel[0]], self.project.get(sel[0])
        if not rec:
            self._res_detail.insert("end", f"{f.name} — 아직 반영되지 않았습니다.")
            return
        lines = [f"{f.name}  ({rec['updated_at']} 반영)", f"출처: {rec.get('source') or ''}", f"근거: {rec.get('basis') or ''}"]
        if rec.get("ref"):
            lines.append(f"참조: {rec['ref']}")
        self._res_detail.insert("end", "\n".join(lines))

    def _on_save_html(self):
        if not self.project.site():
            self.set_status("먼저 1 설치위치 탭에서 좌표를 정해 주세요.")
            return
        name = self.project.name or "KOMPAS"
        start = str(Path(self.project.path).parent) if self.project.path else None
        path = filedialog.asksaveasfilename(title="HTML로 저장", defaultextension=".html", filetypes=[("HTML", "*.html")],
                                            initialdir=start, initialfile=f"{name}.html")
        if not path:
            return
        try:
            files.write_text(path, report_html.build(self.project, self.app_version), newline="\n")
        except (OSError, UnicodeEncodeError) as e:
            messagebox.showerror("저장하지 못했습니다", f"{files.why(e)}.\n\n{path}")
            return
        self.set_status(f"HTML을 저장했습니다: {Path(path).name}")
        try:
            os.startfile(path)          # 기본 브라우저로 열기
        except OSError:
            pass
