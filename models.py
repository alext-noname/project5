from dataclasses import dataclass, field
from datetime import date


def validate_due_date(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("error_deadline_format") from error
    if parsed.isoformat() != value:
        raise ValueError("error_deadline_format")
    return value


@dataclass
class HomeworkTask:
    id: str
    title: str
    due_date: str
    completed: bool = False

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("error_title_required")
        self.due_date = validate_due_date(self.due_date)


@dataclass
class Subject:
    id: str
    name: str
    tasks: list[HomeworkTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("error_subject_required")
