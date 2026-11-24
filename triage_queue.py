from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Patient:
    name: str
    triage_level: int
    arrived_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if type(self.triage_level) is not int or self.triage_level not in (1, 2, 3):
            raise ValueError("El nivel de triaje debe ser un entero entre 1 y 3.")