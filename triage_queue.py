import heapq
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count


@dataclass(frozen=True)
class Patient:
    name: str
    triage_level: int
    arrived_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if type(self.triage_level) is not int or self.triage_level not in (1, 2, 3):
            raise ValueError("El nivel de triaje debe ser un entero entre 1 y 3.")


class TriageQueue:
    def __init__(self) -> None:
        self._patients: list[tuple[int, datetime, int, Patient]] = []
        self._sequence = count()

    def enqueue(self, patient: Patient) -> None:
        arrived_at = patient.arrived_at
        if not isinstance(arrived_at, datetime) or arrived_at.utcoffset() is None:
            raise ValueError("La fecha de llegada debe incluir una zona horaria.")
        heapq.heappush(
            self._patients,
            (
                patient.triage_level,
                arrived_at.astimezone(timezone.utc),
                next(self._sequence),
                patient,
            ),
        )

    def dequeue(self) -> Patient:
        if not self._patients:
            raise IndexError("No hay pacientes en la cola.")
        return heapq.heappop(self._patients)[3]

    def peek(self) -> Patient:
        if not self._patients:
            raise IndexError("No hay pacientes en la cola.")
        return self._patients[0][3]

    def list_queue(self) -> list[Patient]:
        return [entry[3] for entry in sorted(self._patients)]

    def stats(self) -> dict[int, int]:
        counts = {1: 0, 2: 0, 3: 0}
        for level, _, _, _ in self._patients:
            counts[level] += 1
        return counts