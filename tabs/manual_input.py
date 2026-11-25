"""직접 입력 카드 — 가지고 있는 자료값(측량 · 보고서 등)을 공공자료 값 대신 넣을 때 (2 ~ 6 공통).

같은 변수에 출처 "직접 입력 — <문서명>"으로 들어갑니다. 출처(문서명)는 꼭 적어야 합니다.
"""
import customtkinter as ctk

from constants import ACCENT, LABEL, TEXT_DIM, F_LABEL, F_LABEL_B
from widgets import section_label, field_entry, card_frame, secondary_button

from schema import FIELDS, make_record
from tabs.common import note_label

MANUAL_PREFIX = "직접 입력"


def is_manual(rec):
    return bool(rec) and str(rec.get("source", "")).startswith(MANUAL_PREFIX)


def manual_doc(rec):
    """기록의 출처에서 문서명만."""
    s = str(rec.get("source", "")) if rec else ""
    return s.split(" — ", 1)[1] if " — " in s else ""


class ManualCard:
    """fields: [(key, 라벨, 꼭 넣을 칸인지, 기본값)] — 숫자 칸. key가 '_dir'로 끝나면(조류 유향 제외) 글자 칸."""

    def __init__(self, parent, title, fields, on_adopt, note=""):
        self.fields = fields
        card = card_frame(parent)
        card.pack(fill="x", pady=(8, 0))
        section_label(card, title).pack(anchor="w", padx=14, pady=(12, 2))
        if note:
            note_label(card, note).pack(anchor="w", padx=14, pady=(0, 6))
        self.vars, self.cur = {}, {}
        for key, label, required, default in fields:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row, text=f"{label}{'' if required else ' (선택)'}", font=F_LABEL, text_color=LABEL,
                         width=200, anchor="w").pack(side="left")
            var = ctk.StringVar(value="" if default is None else f"{default:g}")
            e = field_entry(row, var, "")
            e.configure(width=90)
            e.pack(side="left")
            ctk.CTkLabel(row, text=FIELDS[key].unit, font=F_LABEL, text_color=TEXT_DIM, width=50, anchor="w").pack(side="left", padx=4)
            cur = ctk.StringVar(value="")
            ctk.CTkLabel(row, textvariable=cur, font=F_LABEL, text_color=TEXT_DIM, anchor="w").pack(side="left", padx=4)
            self.vars[key], self.cur[key] = var, cur
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(6, 2))
        ctk.CTkLabel(row, text="출처 (문서명 · 일자)", font=F_LABEL_B, text_color=LABEL, width=200, anchor="w").pack(side="left")
        self.doc = ctk.StringVar()
        field_entry(row, self.doc, "예: ○○ 측량 보고서 (2026-05-28)").pack(side="left", fill="x", expand=True)
        secondary_button(card, "직접 입력값 반영", on_adopt, width=0).pack(fill="x", padx=14, pady=(6, 4))
        self.state = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self.state, font=F_LABEL_B, text_color=ACCENT, anchor="w", justify="left",
                     wraplength=600).pack(fill="x", padx=14, pady=(0, 12))

    def parse(self):
        """(값 dict, 오류 목록). 빈 선택 칸은 값에 넣지 않음."""
        vals, errs = {}, []
        for key, label, required, _ in self.fields:
            raw = self.vars[key].get().strip()
            if not raw:
                if required:
                    errs.append(f"{label}: 값을 넣으세요")
                continue
            if key.endswith("_dir") and not key.startswith("current_"):
                vals[key] = raw.upper()
                continue
            try:
                vals[key] = float(raw)
            except ValueError:
                errs.append(f"{label}: 숫자가 아닙니다 ({raw})")
        if not self.doc.get().strip():
            errs.append("출처(문서명 · 일자)를 적어 주세요")
        return vals, errs

    def records(self, project, vals, basis=None):
        """basis: {key: 근거 문장} — 없으면 '직접 입력'."""
        src, site = f"{MANUAL_PREFIX} — {self.doc.get().strip()}", project.site()
        return {k: make_record(k, v, src, (basis or {}).get(k, "직접 입력"), site=site) for k, v in vals.items()}

    def refresh(self, project):
        """칸 옆에 지금 반영된 값 표시. 직접 입력으로 반영된 값이 있고 칸이 비었으면 채움."""
        manual_any = None
        for key, *_ in self.fields:
            rec = project.get(key)
            if not rec:
                self.cur[key].set("")
                continue
            v = rec["value"]
            kind = "직접 입력" if is_manual(rec) else "공공자료"
            self.cur[key].set(f"지금: {v:g} ({kind})" if isinstance(v, (int, float)) else f"지금: {v} ({kind})")
            if is_manual(rec):
                manual_any = rec
                default = next(d for k, _, _, d in self.fields if k == key)
                raw = self.vars[key].get().strip()
                if not raw or (default is not None and raw == f"{default:g}"):
                    self.vars[key].set(f"{v:g}" if isinstance(v, (int, float)) else str(v))
        if manual_any and not self.doc.get().strip():
            self.doc.set(manual_doc(manual_any))
        self.state.set(f"직접 입력값 반영 중 — 출처: {manual_doc(manual_any)}" if manual_any else "")
