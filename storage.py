import json
from dataclasses import asdict, replace
from pathlib import Path
from uuid import uuid4

from models import HomeworkTask, Subject


THEMES = ("Светлая", "Тёмная")
LANGUAGES = ("ru", "uk", "en")
EXPORT_FORMAT = "homework-tracker-list"


class HomeworkStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.theme = THEMES[0]
        self.language = "ru"
        self.subjects = self._load()

    def _load(self) -> list[Subject]:
        if not self.path.exists():
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"Не удалось прочитать файл с заданиями: {self.path}") from error
        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("subjects"), list)
        ):
            raise ValueError(f"Неизвестный формат файла с заданиями: {self.path}")
        theme = data.get("theme", THEMES[0])
        if theme not in THEMES:
            raise ValueError(f"Неизвестная тема в файле с заданиями: {self.path}")
        language = data.get("language", "ru")
        if language not in LANGUAGES:
            raise ValueError(f"Неизвестный язык в файле с заданиями: {self.path}")
        try:
            subjects = [
                Subject(
                    id=item["id"],
                    name=item["name"],
                    tasks=[
                        HomeworkTask(
                            id=task["id"],
                            title=task["title"],
                            due_date=task.get("due_date", ""),
                            completed=task.get("completed", False),
                        )
                        for task in item["tasks"]
                    ],
                )
                for item in data["subjects"]
            ]
        except (KeyError, TypeError) as error:
            raise ValueError(f"Не удалось прочитать файл с заданиями: {self.path}") from error
        self.theme = theme
        self.language = language
        return subjects

    def _save(self) -> None:
        data = {
            "version": 1,
            "theme": self.theme,
            "language": self.language,
            "subjects": [asdict(subject) for subject in self.subjects],
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_subject(self, name: str) -> Subject:
        subject = Subject(id=uuid4().hex, name=name)
        if any(existing.name.casefold() == subject.name.casefold() for existing in self.subjects):
            raise ValueError("error_duplicate_subject")
        self.subjects.append(subject)
        self._save()
        return subject

    def update_subject(self, subject_id: str, name: str) -> Subject:
        subject = self._subject(subject_id)
        updated = Subject(id=subject_id, name=name)
        if any(
            existing.id != subject_id
            and existing.name.casefold() == updated.name.casefold()
            for existing in self.subjects
        ):
            raise ValueError("error_duplicate_subject")
        subject.name = updated.name
        self._save()
        return subject

    def move_subject(self, subject_id: str, direction: int) -> bool:
        if direction not in (-1, 1):
            raise ValueError("error_move_direction")
        subject = self._subject(subject_id)
        index = self.subjects.index(subject)
        target_index = index + direction
        if not 0 <= target_index < len(self.subjects):
            return False
        self.subjects[index], self.subjects[target_index] = (
            self.subjects[target_index],
            self.subjects[index],
        )
        self._save()
        return True

    def add_task(self, subject_id: str, title: str, due_date: str) -> HomeworkTask:
        task = HomeworkTask(
            id=uuid4().hex,
            title=title,
            due_date=due_date,
        )
        self._subject(subject_id).tasks.append(task)
        self._save()
        return task

    def update_task(
        self,
        subject_id: str,
        task_id: str,
        title: str,
        due_date: str,
    ) -> HomeworkTask:
        task = HomeworkTask(
            id=task_id,
            title=title,
            due_date=due_date,
            completed=self._task(subject_id, task_id).completed,
        )
        subject = self._subject(subject_id)
        subject.tasks = [
            task if existing.id == task_id else existing
            for existing in subject.tasks
        ]
        self._save()
        return task

    def set_theme(self, theme: str) -> None:
        if theme not in THEMES:
            raise ValueError("error_theme_invalid")
        self.theme = theme
        self._save()

    def set_language(self, language: str) -> None:
        if language not in LANGUAGES:
            raise ValueError("error_language_invalid")
        self.language = language
        self._save()

    def export_json(self) -> str:
        data = {
            "format": EXPORT_FORMAT,
            "version": 1,
            "subjects": [
                {
                    "name": subject.name,
                    "tasks": [
                        {
                            "title": task.title,
                            "due_date": task.due_date,
                            "completed": task.completed,
                        }
                        for task in subject.tasks
                    ],
                }
                for subject in self.subjects
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_json(self, payload: str) -> tuple[int, int]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError("error_import_invalid") from error
        if (
            not isinstance(data, dict)
            or data.get("format") != EXPORT_FORMAT
            or data.get("version") != 1
            or not isinstance(data.get("subjects"), list)
        ):
            raise ValueError("error_import_invalid")

        imported_subjects = []
        try:
            for item in data["subjects"]:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("name"), str)
                    or not isinstance(item.get("tasks"), list)
                ):
                    raise ValueError("error_import_invalid")
                tasks = []
                for task in item["tasks"]:
                    if (
                        not isinstance(task, dict)
                        or not isinstance(task.get("title"), str)
                        or not isinstance(task.get("due_date", ""), str)
                        or not isinstance(task.get("completed", False), bool)
                    ):
                        raise ValueError("error_import_invalid")
                    tasks.append(
                        HomeworkTask(
                            id=uuid4().hex,
                            title=task["title"],
                            due_date=task.get("due_date", ""),
                            completed=task.get("completed", False),
                        )
                    )
                imported_subjects.append(
                    Subject(
                        id=uuid4().hex,
                        name=item["name"],
                        tasks=tasks,
                    )
                )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("error_import_invalid") from error

        subjects_by_name = {
            subject.name.casefold(): subject for subject in self.subjects
        }
        added_subjects = 0
        added_tasks = 0
        for incoming in imported_subjects:
            subject_key = incoming.name.casefold()
            subject = subjects_by_name.get(subject_key)
            if subject is None:
                subject = Subject(id=incoming.id, name=incoming.name)
                self.subjects.append(subject)
                subjects_by_name[subject_key] = subject
                added_subjects += 1

            existing_tasks = {
                (task.title.casefold(), task.due_date)
                for task in subject.tasks
            }
            for task in incoming.tasks:
                task_key = (task.title.casefold(), task.due_date)
                if task_key in existing_tasks:
                    continue
                subject.tasks.append(task)
                existing_tasks.add(task_key)
                added_tasks += 1

        if added_subjects or added_tasks:
            self._save()
        return added_subjects, added_tasks

    def toggle_task(self, subject_id: str, task_id: str) -> HomeworkTask:
        subject = self._subject(subject_id)
        for index, task in enumerate(subject.tasks):
            if task.id == task_id:
                updated = replace(task, completed=not task.completed)
                subject.tasks[index] = updated
                self._save()
                return updated
        raise KeyError("Задание не найдено.")

    def delete_task(self, subject_id: str, task_id: str) -> None:
        subject = self._subject(subject_id)
        remaining = [task for task in subject.tasks if task.id != task_id]
        if len(remaining) == len(subject.tasks):
            raise KeyError("Задание не найдено.")
        subject.tasks = remaining
        self._save()

    def _subject(self, subject_id: str) -> Subject:
        for subject in self.subjects:
            if subject.id == subject_id:
                return subject
        raise KeyError("Предмет не найден.")

    def _task(self, subject_id: str, task_id: str) -> HomeworkTask:
        subject = self._subject(subject_id)
        for task in subject.tasks:
            if task.id == task_id:
                return task
        raise KeyError("Задание не найдено.")
