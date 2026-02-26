import json
import os
import glob
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox
from typing import List, Optional


# =============================
# Data Models
# =============================
@dataclass
class Citation:
    source: str
    section: str
    page: str


@dataclass
class Question:
    qid: str
    stem: str
    choices: List[str]
    correct_index: int
    explanation: str
    citations: List[Citation]


# =============================
# Loading
# =============================
MAX_JSON_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB guardrail per question file.
DEFAULT_QUESTIONS_DIRNAME = "questions"


def load_questions(json_path: str) -> List[Question]:
    try:
        size = os.path.getsize(json_path)
    except OSError as e:
        raise ValueError(f"Cannot access file {os.path.basename(json_path)}: {e}") from e

    if size > MAX_JSON_FILE_SIZE_BYTES:
        raise ValueError(
            f"{os.path.basename(json_path)} is too large ({size} bytes). "
            f"Limit is {MAX_JSON_FILE_SIZE_BYTES} bytes."
        )

    try:
        # utf-8-sig handles normal UTF-8 and UTF-8 with BOM.
        with open(json_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {os.path.basename(json_path)}: {e}") from e
    except OSError as e:
        raise ValueError(f"Cannot read file {os.path.basename(json_path)}: {e}") from e

    if "questions" not in data or not isinstance(data["questions"], list):
        raise ValueError(f"Invalid JSON structure in: {json_path} (missing 'questions' list)")

    questions: List[Question] = []
    for item in data["questions"]:
        qid = item.get("qid", "(missing qid)")
        choices = item.get("choices", [])
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError(f"{qid} in {os.path.basename(json_path)} must have exactly 4 choices")

        ci = item.get("correct_index", None)
        if ci not in (0, 1, 2, 3):
            raise ValueError(f"{qid} in {os.path.basename(json_path)} correct_index must be 0..3")

        citations = []
        for c in item.get("citations", []):
            citations.append(
                Citation(
                    source=str(c.get("source", "")),
                    section=str(c.get("section", "")),
                    page=str(c.get("page", "")),
                )
            )

        questions.append(
            Question(
                qid=str(item.get("qid", "")),
                stem=str(item.get("stem", "")),
                choices=[str(x) for x in choices],
                correct_index=int(ci),
                explanation=str(item.get("explanation", "")),
                citations=citations,
            )
        )

    return questions


def discover_json_files(base_dir: str) -> List[str]:
    paths = []
    for name in os.listdir(base_dir):
        p = os.path.join(base_dir, name)
        if os.path.isfile(p) and os.path.splitext(name)[1].lower() == ".json":
            paths.append(p)
    paths.sort(key=lambda p: os.path.basename(p).lower())
    return paths


def discover_json_files_recursive(base_dir: str) -> List[str]:
    paths: List[str] = []
    for root, _, files in os.walk(base_dir):
        for name in files:
            if os.path.splitext(name)[1].lower() == ".json":
                paths.append(os.path.join(root, name))
    paths.sort(key=lambda p: p.lower())
    return paths


def get_runtime_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_default_questions_dir(runtime_base_dir: str) -> str:
    candidate = os.path.join(runtime_base_dir, DEFAULT_QUESTIONS_DIRNAME)
    if os.path.isdir(candidate):
        return candidate
    return runtime_base_dir


def build_question_set(selected_files: List[str]) -> List[Question]:
    all_questions: List[Question] = []
    seen_qids = set()

    for path in selected_files:
        qs = load_questions(path)
        for q in qs:
            qid = q.qid.strip() if q.qid else ""
            if qid and qid in seen_qids:
                prefix = os.path.splitext(os.path.basename(path))[0]
                q.qid = f"{prefix}:{qid}"
            if q.qid:
                seen_qids.add(q.qid)
            all_questions.append(q)

    return all_questions


# =============================
# File Picker UI
# =============================
class FilePicker(tk.Tk):
    def __init__(self, start_dir: str):
        super().__init__()
        self.title("Select Question Sets")
        self.geometry("720x460")

        self.current_dir = start_dir
        self.json_files = discover_json_files(start_dir)
        self.display_names: List[str] = []
        self.selection: Optional[List[str]] = None

        self._build_ui()

    def _build_ui(self):
        header = tk.Label(
            self,
            text="Select one or more question files to run",
            font=("Segoe UI", 12),
            anchor="w",
            padx=14,
            pady=10,
        )
        header.pack(fill="x")

        hint = tk.Label(
            self,
            text="Tip: Hold Ctrl to select multiple (Shift selects a range).",
            font=("Segoe UI", 10),
            anchor="w",
            padx=14,
        )
        hint.pack(fill="x")

        self.folder_label = tk.Label(
            self,
            text=f"Folder: {self.current_dir}",
            font=("Segoe UI", 9),
            anchor="w",
            padx=14,
        )
        self.folder_label.pack(fill="x")

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=14, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            frame,
            selectmode="extended",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        self._refresh_listbox()

        controls = tk.Frame(self)
        controls.pack(fill="x", padx=14, pady=(0, 14))

        tk.Button(controls, text="Browse Folder", width=14, command=self._browse_folder).pack(side="left")
        tk.Button(controls, text="Browse Files", width=12, command=self._browse_files).pack(side="left", padx=(8, 0))
        tk.Button(controls, text="Select All", width=12, command=self._select_all).pack(side="left")
        tk.Button(controls, text="Clear", width=12, command=self._clear).pack(side="left", padx=(8, 0))

        tk.Button(controls, text="Start Quiz", width=14, command=self._start).pack(side="right")
        tk.Button(controls, text="Cancel", width=12, command=self._cancel).pack(side="right", padx=(0, 8))

    def _refresh_listbox(self):
        self.listbox.delete(0, "end")
        self.display_names = []
        for p in self.json_files:
            try:
                label = os.path.relpath(p, self.current_dir)
            except ValueError:
                label = os.path.basename(p)
            self.display_names.append(label)
            self.listbox.insert("end", label)

    def _browse_folder(self):
        picked = filedialog.askdirectory(initialdir=self.current_dir, title="Select folder with question JSON files")
        if not picked:
            return

        self.current_dir = picked
        self.json_files = discover_json_files(self.current_dir)
        if not self.json_files:
            self.json_files = discover_json_files_recursive(self.current_dir)
        self.folder_label.config(text=f"Folder: {self.current_dir}")
        self._refresh_listbox()

        if not self.json_files:
            messagebox.showwarning("No JSON files", f"No .json files found in: {self.current_dir}")

    def _browse_files(self):
        picked = filedialog.askopenfilenames(
            initialdir=self.current_dir,
            title="Select question JSON files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not picked:
            return

        self.json_files = sorted(set(picked), key=lambda p: p.lower())
        self._refresh_listbox()

    def _select_all(self):
        if not self.json_files:
            return
        self.listbox.select_set(0, "end")

    def _clear(self):
        self.listbox.selection_clear(0, "end")

    def _start(self):
        if not self.json_files:
            messagebox.showwarning("No files", "No .json files are available in the selected folder.")
            return

        indices = list(self.listbox.curselection())
        if not indices:
            messagebox.showwarning("No selection", "Select at least one file.")
            return

        self.selection = [self.json_files[i] for i in indices]
        self.destroy()

    def _cancel(self):
        self.selection = None
        self.destroy()


# =============================
# Quiz Application
# =============================
class QuizApp(tk.Tk):
    def __init__(self, questions: List[Question], source_files: List[str]):
        super().__init__()

        self.title("PMP Practice Quiz")
        self.geometry("980x640")

        self.questions = questions
        self.total = len(questions)
        self.current = 0

        self.source_files = source_files

        self.selected: List[Optional[int]] = [None] * self.total
        self.correct: List[Optional[bool]] = [None] * self.total
        self.show_explanations_var = tk.BooleanVar(value=False)

        self.build_ui()
        self.render_question()

    def build_ui(self):
        topbar = tk.Frame(self)
        topbar.pack(fill="x", padx=20, pady=(12, 0))

        self.files_label = tk.Label(
            topbar,
            text="Loaded: " + ", ".join(os.path.basename(p) for p in self.source_files),
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.files_label.pack(fill="x")

        self.stem_label = tk.Label(
            self, text="", anchor="nw", justify="left",
            wraplength=920, font=("Segoe UI", 12)
        )
        self.stem_label.pack(fill="x", padx=20, pady=(10, 8))

        self.choice_var = tk.IntVar(value=-1)
        self.choice_frame = tk.Frame(self)
        self.choice_frame.pack(fill="both", expand=True, padx=20)

        self.choice_buttons: List[tk.Radiobutton] = []
        for i in range(4):
            rb = tk.Radiobutton(
                self.choice_frame,
                text="",
                variable=self.choice_var,
                value=i,
                anchor="w",
                justify="left",
                wraplength=900,
                font=("Segoe UI", 11),
                command=self.select_answer
            )
            rb.pack(fill="x", pady=6)
            self.choice_buttons.append(rb)

        self.explanation_label = tk.Label(
            self,
            text="",
            anchor="w",
            justify="left",
            wraplength=920,
            font=("Segoe UI", 10, "italic"),
            fg="#234a8a",
            padx=20,
            pady=4,
        )
        self.explanation_label.pack(fill="x", padx=20, pady=(2, 2))

        control = tk.Frame(self)
        control.pack(fill="x", padx=20, pady=10)

        tk.Button(control, text="Previous", width=12, command=self.prev).pack(side="left")
        tk.Button(control, text="Next", width=12, command=self.next).pack(side="left", padx=8)

        tk.Button(control, text="Reset", width=12, command=self.reset_quiz).pack(side="left", padx=8)
        tk.Button(control, text="Load New Questions", width=18, command=self.load_new_questions).pack(side="left", padx=8)
        tk.Checkbutton(
            control,
            text="Show Explanation After Answer",
            variable=self.show_explanations_var,
            command=self.update_explanation_display,
        ).pack(side="left", padx=(12, 0))

        tk.Button(control, text="Finish and Grade", width=18, command=self.finish).pack(side="right")

        self.status = tk.Label(control, text="", font=("Segoe UI", 10), anchor="w")
        self.status.pack(side="left", padx=20)

        nav_wrap = tk.Frame(self)
        nav_wrap.pack(fill="x", padx=20, pady=(6, 16))

        tk.Label(nav_wrap, text="Questions:", font=("Segoe UI", 10)).pack(anchor="w")

        self.nav = tk.Frame(nav_wrap)
        self.nav.pack(fill="x", pady=(6, 0))

        self.nav_buttons: List[tk.Button] = []
        self.rebuild_nav()

    def rebuild_nav(self):
        for b in getattr(self, "nav_buttons", []):
            b.destroy()
        self.nav_buttons = []

        for i in range(self.total):
            b = tk.Button(
                self.nav,
                text=str(i + 1),
                width=3,
                bg="#d9d9d9",
                command=lambda x=i: self.goto(x)
            )
            b.pack(side="left", padx=2, pady=2)
            self.nav_buttons.append(b)

    def render_question(self):
        q = self.questions[self.current]
        self.stem_label.config(
            text=f"Question {self.current + 1} of {self.total} [{q.qid}]\n\n{q.stem}"
        )

        for i in range(4):
            self.choice_buttons[i].config(text=q.choices[i])

        self.choice_var.set(self.selected[self.current] if self.selected[self.current] is not None else -1)
        self.update_explanation_display()
        self.update_status()

    def select_answer(self):
        pick = self.choice_var.get()
        if pick not in (0, 1, 2, 3):
            return

        self.selected[self.current] = pick
        self.correct[self.current] = (pick == self.questions[self.current].correct_index)

        self.nav_buttons[self.current].config(
            bg="#6cc070" if self.correct[self.current] else "#d66a6a"
        )
        self.update_explanation_display()
        self.update_status()

    def update_status(self):
        answered = sum(1 for x in self.selected if x is not None)
        correct = sum(1 for x in self.correct if x is True)
        self.status.config(text=f"Answered {answered}/{self.total}   Correct {correct}")

    def update_explanation_display(self):
        if not self.show_explanations_var.get():
            self.explanation_label.config(text="")
            return

        pick = self.selected[self.current]
        if pick is None:
            self.explanation_label.config(text="")
            return

        q = self.questions[self.current]
        explanation = q.explanation.strip() if q.explanation else ""
        if not explanation:
            explanation = "No explanation for this question."

        if self.correct[self.current]:
            prefix = "Correct."
        else:
            prefix = "Incorrect."

        self.explanation_label.config(text=f"{prefix} {explanation}")

    def goto(self, index: int):
        self.current = index
        self.render_question()

    def prev(self):
        if self.current > 0:
            self.current -= 1
            self.render_question()

    def next(self):
        if self.current < self.total - 1:
            self.current += 1
            self.render_question()

    def reset_quiz(self):
        if not messagebox.askyesno("Reset Quiz", "Reset will clear all answers and start over. Continue?"):
            return

        self.selected = [None] * self.total
        self.correct = [None] * self.total
        self.current = 0
        self.choice_var.set(-1)

        for b in self.nav_buttons:
            b.config(bg="#d9d9d9")

        self.render_question()

    def load_new_questions(self):
        if not messagebox.askyesno("Load New Questions", "This will replace the current question set. Continue?"):
            return

        runtime_base_dir = get_runtime_base_dir()
        questions_dir = get_default_questions_dir(runtime_base_dir)
        picker = FilePicker(questions_dir)
        picker.mainloop()

        if not picker.selection:
            return

        try:
            new_questions = build_question_set(picker.selection)
        except ValueError as e:
            messagebox.showerror("Invalid question file", str(e))
            return

        if not new_questions:
            messagebox.showerror("No questions", "No questions loaded from selected files.")
            return

        self.questions = new_questions
        self.total = len(new_questions)
        self.current = 0
        self.source_files = picker.selection

        self.selected = [None] * self.total
        self.correct = [None] * self.total
        self.choice_var.set(-1)

        self.files_label.config(
            text="Loaded: " + ", ".join(os.path.basename(p) for p in self.source_files)
        )

        self.rebuild_nav()
        self.render_question()

    def finish(self):
        correct_count = sum(1 for x in self.correct if x is True)
        score = (correct_count / self.total) * 100 if self.total else 0.0

        report_lines: List[str] = []
        report_lines.append("PMP Quiz Report")
        report_lines.append("")
        report_lines.append("Files used:")
        for p in self.source_files:
            report_lines.append(f"  - {os.path.basename(p)}")
        report_lines.append("")
        report_lines.append(f"Score: {correct_count}/{self.total} ({score:.1f}%)")
        report_lines.append("")

        had_missed = False
        for i, q in enumerate(self.questions):
            if self.selected[i] is None:
                continue
            if self.correct[i] is False:
                had_missed = True
                picked = self.selected[i]
                ci = q.correct_index

                report_lines.append(f"Question {i + 1} [{q.qid}]")
                report_lines.append(q.stem)
                report_lines.append("")
                report_lines.append(f"Your answer: {chr(65 + picked)}. {q.choices[picked]}")
                report_lines.append(f"Correct answer: {chr(65 + ci)}. {q.choices[ci]}")
                if q.explanation:
                    report_lines.append(f"Why: {q.explanation}")
                if q.citations:
                    report_lines.append("Where to study:")
                    for c in q.citations:
                        page_part = f" | page {c.page}" if c.page else ""
                        report_lines.append(f"  - {c.source} | {c.section}{page_part}")
                report_lines.append("")
                report_lines.append("-" * 60)
                report_lines.append("")

        if not had_missed:
            report_lines.append("No incorrect answers to review.")

        top = tk.Toplevel(self)
        top.title("Results")
        top.geometry("980x640")

        text = tk.Text(top, wrap="word", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert("1.0", "\n".join(report_lines))
        text.config(state="disabled")


# =============================
# Main
# =============================
def main():
    runtime_base_dir = get_runtime_base_dir()
    questions_dir = get_default_questions_dir(runtime_base_dir)
    picker = FilePicker(questions_dir)
    picker.mainloop()

    if not picker.selection:
        return

    try:
        questions = build_question_set(picker.selection)
    except ValueError as e:
        messagebox.showerror("Invalid question file", str(e))
        return

    if not questions:
        messagebox.showerror("No questions", "No questions loaded from selected files.")
        return

    app = QuizApp(questions, picker.selection)
    app.mainloop()


if __name__ == "__main__":
    main()
