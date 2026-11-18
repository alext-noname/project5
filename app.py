import ctypes
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from i18n import LANGUAGE_NAMES, translate
from models import HomeworkTask, Subject
from storage import THEMES, HomeworkStore


DATA_PATH = Path(__file__).resolve().parent / "data" / "homework.json"
RICKROLL_URL = (
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    "&list=RDdQw4w9WgXcQ&start_radio=1"
)


def _enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    user32 = ctypes.windll.user32
    try:
        set_awareness = user32.SetProcessDpiAwarenessContext
    except AttributeError:
        try:
            set_awareness = ctypes.windll.shcore.SetProcessDpiAwareness
        except AttributeError:
            user32.SetProcessDPIAware()
        else:
            set_awareness(2)
    else:
        set_awareness.argtypes = [ctypes.c_void_p]
        set_awareness.restype = ctypes.c_bool
        set_awareness(ctypes.c_void_p(-4))


class HomeworkApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.iconbitmap(
            default=str(Path(__file__).resolve().parent / "homework.ico")
        )
        self.geometry("1000x680")
        self.minsize(850, 580)
        self.store = HomeworkStore(DATA_PATH)
        self.selected_subject_id: str | None = None
        self.style = ttk.Style(self)
        self.theme = tk.StringVar(value=self.store.theme)
        self.language = tk.StringVar(value=self.store.language)
        self._copy_click_count = 0
        self._copy_click_timer_id: str | None = None

        self._build_ui()
        self._apply_theme()
        self._refresh_subjects()

    def _tr(self, key: str, **values: object) -> str:
        return translate(self.language.get(), key, **values)

    def _build_ui(self) -> None:
        self.title(self._tr("app_title"))
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.home = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.home, text=self._tr("home_tab"))
        self.home.columnconfigure(1, weight=1)
        self.home.rowconfigure(0, weight=1)

        subjects_panel = ttk.LabelFrame(
            self.home,
            text=self._tr("subjects"),
            padding=10,
        )
        subjects_panel.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        subjects_panel.rowconfigure(1, weight=1)

        self.subject_name = tk.StringVar()
        subject_entry = ttk.Entry(
            subjects_panel,
            textvariable=self.subject_name,
            width=25,
        )
        subject_entry.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        subject_entry.bind("<Return>", lambda _event: self._add_subject())
        ttk.Button(
            subjects_panel,
            text=self._tr("add_subject"),
            command=self._add_subject,
        ).grid(row=0, column=1, padx=(8, 0), pady=(0, 8))

        self.subjects_list = ttk.Treeview(
            subjects_panel,
            show="tree",
            height=18,
            selectmode="browse",
        )
        self.subjects_list.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.subjects_list.bind("<<TreeviewSelect>>", self._on_subject_selected)
        move_controls = ttk.Frame(subjects_panel)
        move_controls.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        move_controls.columnconfigure(0, weight=1)
        move_controls.columnconfigure(1, weight=1)
        self.move_subject_up_button = ttk.Button(
            move_controls,
            text=self._tr("move_up"),
            command=lambda: self._move_selected_subject(-1),
        )
        self.move_subject_up_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.move_subject_down_button = ttk.Button(
            move_controls,
            text=self._tr("move_down"),
            command=lambda: self._move_selected_subject(1),
        )
        self.move_subject_down_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(
            subjects_panel,
            text=self._tr("rename_subject"),
            command=self._rename_subject,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        tasks_panel = ttk.LabelFrame(
            self.home,
            text=self._tr("task_list"),
            padding=10,
        )
        tasks_panel.grid(row=0, column=1, sticky="nsew")
        tasks_panel.columnconfigure(0, weight=1)
        tasks_panel.rowconfigure(1, weight=1)

        self.current_subject_label = ttk.Label(
            tasks_panel,
            text=self._tr("choose_subject"),
        )
        self.current_subject_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        columns = ("title", "due_date", "status")
        self.tasks_list = ttk.Treeview(
            tasks_panel,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tasks_list.heading("title", text=self._tr("task"))
        self.tasks_list.heading("due_date", text=self._tr("deadline"))
        self.tasks_list.heading("status", text=self._tr("status"))
        for column, anchor in (
            ("title", "w"),
            ("due_date", "center"),
            ("status", "center"),
        ):
            self.tasks_list.column(
                column,
                width=150,
                minwidth=100,
                stretch=True,
                anchor=anchor,
            )
        self.tasks_list.grid(row=1, column=0, sticky="nsew")
        self.tasks_list.bind("<Button-1>", self._lock_task_column_width)

        tasks_scroll = ttk.Scrollbar(
            tasks_panel,
            orient="vertical",
            command=self.tasks_list.yview,
        )
        tasks_scroll.grid(row=1, column=1, sticky="ns")
        self.tasks_list.configure(yscrollcommand=tasks_scroll.set)
        self.tasks_list.bind("<Double-1>", lambda _event: self._edit_task())

        form = ttk.LabelFrame(
            tasks_panel,
            text=self._tr("new_task"),
            padding=10,
        )
        form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text=self._tr("title")).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )
        self.task_title = tk.StringVar()
        ttk.Entry(form, textvariable=self.task_title).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(form, text=self._tr("deadline")).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )
        self.due_date = tk.StringVar()
        ttk.Entry(form, textvariable=self.due_date, width=30).grid(
            row=1,
            column=1,
            sticky="w",
            pady=4,
        )

        actions = ttk.Frame(tasks_panel)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(
            actions,
            text=self._tr("add_task"),
            command=self._add_task,
        ).pack(side="left")
        ttk.Button(
            actions,
            text=self._tr("edit_task"),
            command=self._edit_task,
        ).pack(side="left", padx=8)
        ttk.Button(
            actions,
            text=self._tr("toggle_task"),
            command=self._toggle_task,
        ).pack(side="left")
        ttk.Button(
            actions,
            text=self._tr("delete_task"),
            command=self._delete_task,
        ).pack(side="left", padx=8)

        self.status_text = tk.StringVar(value=self._tr("local_data_note"))
        ttk.Label(self, textvariable=self.status_text, anchor="w").pack(
            fill="x",
            padx=14,
            pady=(0, 8),
        )

        self.settings = ttk.Frame(self.notebook, padding=24)
        self.notebook.add(self.settings, text=self._tr("settings_tab"))

        theme_panel = ttk.LabelFrame(
            self.settings,
            text=self._tr("theme_section"),
            padding=12,
        )
        theme_panel.pack(fill="x", anchor="w", pady=(0, 12))
        for theme_name, label_key in (
            (THEMES[0], "theme_light"),
            (THEMES[1], "theme_dark"),
        ):
            ttk.Radiobutton(
                theme_panel,
                text=self._tr(label_key),
                value=theme_name,
                variable=self.theme,
                command=self._change_theme,
            ).pack(anchor="w", pady=4)

        language_panel = ttk.LabelFrame(
            self.settings,
            text=self._tr("language_section"),
            padding=12,
        )
        language_panel.pack(fill="x", anchor="w", pady=(0, 12))
        for language_code, language_name in LANGUAGE_NAMES.items():
            ttk.Radiobutton(
                language_panel,
                text=language_name,
                value=language_code,
                variable=self.language,
                command=self._change_language,
            ).pack(anchor="w", pady=4)

        transfer_panel = ttk.LabelFrame(
            self.settings,
            text=self._tr("transfer_section"),
            padding=12,
        )
        transfer_panel.pack(fill="x", anchor="w")
        ttk.Button(
            transfer_panel,
            text=self._tr("copy_tasks"),
            command=self._copy_task_list,
        ).pack(anchor="w", pady=4)
        ttk.Button(
            transfer_panel,
            text=self._tr("paste_tasks"),
            command=self._paste_task_list,
        ).pack(anchor="w", pady=4)

    def _apply_theme(self) -> None:
        dark = self.theme.get() == THEMES[1]
        colors = {
            "background": "#202531" if dark else "#f2f4f8",
            "surface": "#2b3240" if dark else "#ffffff",
            "text": "#e8eaf0" if dark else "#202633",
            "muted": "#aeb7c6" if dark else "#657080",
            "field": "#252c39" if dark else "#ffffff",
            "border": "#465064" if dark else "#d7dce5",
            "accent": "#4569a8" if dark else "#dce8fb",
            "selected_text": "#ffffff" if dark else "#202633",
            "completed": "#91c49a" if dark else "#63806b",
        }
        self.style.theme_use("clam")
        self.configure(background=colors["background"])
        self.style.configure(
            ".",
            background=colors["background"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        self.style.configure("TFrame", background=colors["background"])
        self.style.configure(
            "TLabelframe",
            background=colors["background"],
            foreground=colors["text"],
            bordercolor=colors["border"],
        )
        self.style.configure(
            "TLabelframe.Label",
            background=colors["background"],
            foreground=colors["text"],
        )
        self.style.configure(
            "TLabel",
            background=colors["background"],
            foreground=colors["text"],
        )
        self.style.configure(
            "TButton",
            background=colors["surface"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            padding=(10, 6),
        )
        self.style.map(
            "TButton",
            background=[("active", colors["accent"]), ("pressed", colors["accent"])],
            foreground=[("disabled", colors["muted"])],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=colors["field"],
            foreground=colors["text"],
            insertcolor=colors["text"],
            bordercolor=colors["border"],
        )
        self.style.configure(
            "TRadiobutton",
            background=colors["background"],
            foreground=colors["text"],
        )
        self.style.map(
            "TRadiobutton",
            background=[("active", colors["background"])],
            foreground=[("active", colors["text"])],
        )
        self.style.configure(
            "TNotebook",
            background=colors["background"],
            borderwidth=0,
        )
        self.style.configure(
            "TNotebook.Tab",
            background=colors["surface"],
            foreground=colors["text"],
            padding=(12, 7),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", colors["accent"])],
            foreground=[("selected", colors["selected_text"])],
        )
        self.style.configure(
            "Treeview",
            background=colors["surface"],
            fieldbackground=colors["surface"],
            foreground=colors["text"],
            rowheight=28,
            bordercolor=colors["border"],
        )
        self.style.map(
            "Treeview",
            background=[("selected", colors["accent"])],
            foreground=[("selected", colors["selected_text"])],
        )
        self.style.configure(
            "Treeview.Heading",
            background=colors["background"],
            foreground=colors["text"],
            relief="flat",
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", colors["accent"])],
        )
        self._theme_colors = colors
        self._refresh_tasks()

    def _change_theme(self) -> None:
        try:
            self.store.set_theme(self.theme.get())
        except ValueError as error:
            messagebox.showerror(
                self._tr("error_theme"),
                self._tr(str(error)),
                parent=self,
            )
            self.theme.set(self.store.theme)
            return
        self._apply_theme()
        self.status_text.set(self._tr("theme_changed", name=self._tr(
            "theme_dark" if self.theme.get() == THEMES[1] else "theme_light"
        )))

    def _change_language(self) -> None:
        try:
            self.store.set_language(self.language.get())
        except ValueError as error:
            messagebox.showerror(
                self._tr("error_language"),
                self._tr(str(error)),
                parent=self,
            )
            self.language.set(self.store.language)
            return

        subject_value = self.subject_name.get()
        title_value = self.task_title.get()
        deadline_value = self.due_date.get()
        selected_id = self.selected_subject_id
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        self.subject_name.set(subject_value)
        self.task_title.set(title_value)
        self.due_date.set(deadline_value)
        self._apply_theme()
        self._refresh_subjects(selected_id)
        self.status_text.set(self._tr("language_changed"))

    def _add_subject(self) -> None:
        try:
            subject = self.store.add_subject(self.subject_name.get())
        except ValueError as error:
            messagebox.showerror(
                self._tr("error_add_subject"),
                self._tr(str(error)),
                parent=self,
            )
            return
        self.subject_name.set("")
        self._refresh_subjects(subject.id)
        self.status_text.set(self._tr("subject_added", name=subject.name))

    def _rename_subject(self) -> None:
        subject = next(
            (item for item in self.store.subjects if item.id == self.selected_subject_id),
            None,
        )
        if subject is None:
            messagebox.showinfo(
                self._tr("select_subject_title"),
                self._tr("select_subject_message"),
                parent=self,
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title(self._tr("rename_subject"))
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        name = tk.StringVar(value=subject.name)
        ttk.Label(dialog, text=self._tr("subject_name_label")).grid(
            row=0,
            column=0,
            padx=12,
            pady=8,
            sticky="w",
        )
        entry = ttk.Entry(dialog, textvariable=name, width=38)
        entry.grid(row=0, column=1, padx=12, pady=8, sticky="ew")
        entry.focus_set()
        entry.selection_range(0, tk.END)

        def save_changes() -> None:
            try:
                updated = self.store.update_subject(subject.id, name.get())
            except ValueError as error:
                messagebox.showerror(
                    self._tr("error_rename_subject"),
                    self._tr(str(error)),
                    parent=dialog,
                )
                return
            dialog.destroy()
            self._refresh_subjects(updated.id)
            self.status_text.set(
                self._tr("subject_renamed", name=updated.name)
            )

        entry.bind("<Return>", lambda _event: save_changes())
        buttons = ttk.Frame(dialog)
        buttons.grid(row=1, column=0, columnspan=2, padx=12, pady=12, sticky="e")
        ttk.Button(
            buttons,
            text=self._tr("save"),
            command=save_changes,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text=self._tr("cancel"),
            command=dialog.destroy,
        ).pack(side="left", padx=(8, 0))

    def _add_task(self) -> None:
        if self.selected_subject_id is None:
            messagebox.showinfo(
                self._tr("select_subject_title"),
                self._tr("select_subject_message"),
                parent=self,
            )
            return
        try:
            task = self.store.add_task(
                self.selected_subject_id,
                self.task_title.get(),
                self.due_date.get(),
            )
        except ValueError as error:
            messagebox.showerror(
                self._tr("error_add_task"),
                self._tr(str(error)),
                parent=self,
            )
            return
        self.task_title.set("")
        self.due_date.set("")
        self._refresh_tasks()
        self.status_text.set(self._tr("task_added", name=task.title))

    def _on_subject_selected(self, _event: tk.Event) -> None:
        selection = self.subjects_list.selection()
        self.selected_subject_id = selection[0] if selection else None
        self._refresh_subject_controls()
        self._refresh_tasks()

    def _refresh_subject_controls(self) -> None:
        selected_index = next(
            (
                index
                for index, subject in enumerate(self.store.subjects)
                if subject.id == self.selected_subject_id
            ),
            None,
        )
        self.move_subject_up_button.configure(
            state="normal" if selected_index is not None and selected_index > 0 else "disabled"
        )
        self.move_subject_down_button.configure(
            state=(
                "normal"
                if selected_index is not None and selected_index < len(self.store.subjects) - 1
                else "disabled"
            )
        )

    def _move_selected_subject(self, direction: int) -> None:
        if self.selected_subject_id is None:
            return
        moved = self.store.move_subject(self.selected_subject_id, direction)
        if not moved:
            return
        self._refresh_subjects(self.selected_subject_id)
        self.status_text.set(
            self._tr("subject_moved_up" if direction < 0 else "subject_moved_down")
        )

    def _lock_task_column_width(self, event: tk.Event) -> str | None:
        if self.tasks_list.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    def _refresh_subjects(self, selected_id: str | None = None) -> None:
        for item in self.subjects_list.get_children():
            self.subjects_list.delete(item)
        for subject in self.store.subjects:
            self.subjects_list.insert("", "end", iid=subject.id, text=subject.name)
        if selected_id is None and self.selected_subject_id:
            selected_id = self.selected_subject_id
        if selected_id and self.subjects_list.exists(selected_id):
            self.subjects_list.selection_set(selected_id)
            self.subjects_list.focus(selected_id)
            self.selected_subject_id = selected_id
        elif self.store.subjects:
            first_id = self.store.subjects[0].id
            self.subjects_list.selection_set(first_id)
            self.subjects_list.focus(first_id)
            self.selected_subject_id = first_id
        else:
            self.selected_subject_id = None
        self._refresh_subject_controls()
        self._refresh_tasks()

    def _refresh_tasks(self) -> None:
        for item in self.tasks_list.get_children():
            self.tasks_list.delete(item)
        subject = next(
            (item for item in self.store.subjects if item.id == self.selected_subject_id),
            None,
        )
        if subject is None:
            self.current_subject_label.configure(text=self._tr("choose_subject"))
            return
        self.current_subject_label.configure(
            text=self._tr("subject_prefix", name=subject.name)
        )
        for task in subject.tasks:
            self.tasks_list.insert(
                "",
                "end",
                iid=task.id,
                values=(
                    task.title,
                    task.due_date or "—",
                    self._tr("completed" if task.completed else "not_completed"),
                ),
                tags=("completed",) if task.completed else (),
            )
        self.tasks_list.tag_configure(
            "completed",
            foreground=self._theme_colors["completed"],
        )

    def _selected_task(self) -> tuple[Subject, HomeworkTask] | None:
        selection = self.tasks_list.selection()
        if not selection:
            messagebox.showinfo(
                self._tr("select_task_title"),
                self._tr("select_task_message"),
                parent=self,
            )
            return None
        subject = next(
            item for item in self.store.subjects if item.id == self.selected_subject_id
        )
        task_id = selection[0]
        task = next(item for item in subject.tasks if item.id == task_id)
        return subject, task

    def _edit_task(self) -> None:
        selected = self._selected_task()
        if selected is None:
            return
        subject, task = selected
        dialog = tk.Toplevel(self)
        dialog.title(self._tr("edit_task"))
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        title = tk.StringVar(value=task.title)
        due_date = tk.StringVar(value=task.due_date)
        ttk.Label(dialog, text=self._tr("title")).grid(
            row=0,
            column=0,
            padx=12,
            pady=8,
            sticky="w",
        )
        ttk.Entry(dialog, textvariable=title, width=38).grid(
            row=0,
            column=1,
            padx=12,
            pady=8,
            sticky="ew",
        )
        ttk.Label(dialog, text=self._tr("deadline")).grid(
            row=1,
            column=0,
            padx=12,
            pady=8,
            sticky="w",
        )
        ttk.Entry(dialog, textvariable=due_date, width=38).grid(
            row=1,
            column=1,
            padx=12,
            pady=8,
            sticky="ew",
        )

        def save_changes() -> None:
            try:
                self.store.update_task(subject.id, task.id, title.get(), due_date.get())
            except ValueError as error:
                messagebox.showerror(
                    self._tr("error_edit_task"),
                    self._tr(str(error)),
                    parent=dialog,
                )
                return
            dialog.destroy()
            self._refresh_tasks()
            self.status_text.set(self._tr("task_changes_saved"))

        buttons = ttk.Frame(dialog)
        buttons.grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="e")
        ttk.Button(
            buttons,
            text=self._tr("save"),
            command=save_changes,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text=self._tr("cancel"),
            command=dialog.destroy,
        ).pack(side="left", padx=(8, 0))

    def _toggle_task(self) -> None:
        selected = self._selected_task()
        if selected is None:
            return
        subject, task = selected
        updated = self.store.toggle_task(subject.id, task.id)
        self._refresh_tasks()
        self.status_text.set(
            self._tr("task_completed" if updated.completed else "task_uncompleted")
        )

    def _delete_task(self) -> None:
        selected = self._selected_task()
        if selected is None:
            return
        subject, task = selected
        if not messagebox.askyesno(
            self._tr("delete_confirmation_title"),
            self._tr("delete_confirmation_message", name=task.title),
            parent=self,
        ):
            return
        self.store.delete_task(subject.id, task.id)
        self._refresh_tasks()
        self.status_text.set(self._tr("task_deleted"))

    def _copy_task_list(self) -> None:
        self._record_copy_click()
        try:
            self.clipboard_clear()
            self.clipboard_append(self.store.export_json())
        except tk.TclError:
            messagebox.showerror(
                self._tr("error_copy"),
                self._tr("error_clipboard"),
                parent=self,
            )
            return
        self.status_text.set(self._tr("clipboard_copied"))

    def _record_copy_click(self) -> None:
        if self._copy_click_timer_id is None:
            self._copy_click_timer_id = self.after(
                3000,
                self._reset_copy_click_count,
            )
        self._copy_click_count += 1
        if self._copy_click_count == 10:
            if self._copy_click_timer_id is not None:
                self.after_cancel(self._copy_click_timer_id)
            self._copy_click_count = 0
            self._copy_click_timer_id = None
            self.after_idle(self._open_video_link)

    def _reset_copy_click_count(self) -> None:
        self._copy_click_count = 0
        self._copy_click_timer_id = None

    def _open_video_link(self) -> None:
        try:
            opened = webbrowser.open(RICKROLL_URL, new=2)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            self.status_text.set(self._tr("error_open_video"))

    def _paste_task_list(self) -> None:
        try:
            payload = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror(
                self._tr("error_import"),
                self._tr("error_clipboard"),
                parent=self,
            )
            return
        try:
            added_subjects, added_tasks = self.store.import_json(payload)
        except ValueError as error:
            messagebox.showerror(
                self._tr("error_import"),
                self._tr(str(error)),
                parent=self,
            )
            return
        self._refresh_subjects(self.selected_subject_id)
        if not added_subjects and not added_tasks:
            self.status_text.set(self._tr("import_no_changes"))
            return
        self.status_text.set(
            self._tr(
                "import_result",
                subjects=added_subjects,
                tasks=added_tasks,
            )
        )


if __name__ == "__main__":
    _enable_windows_dpi_awareness()
    HomeworkApp().mainloop()
