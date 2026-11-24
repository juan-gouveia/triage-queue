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


class TriageCLI:
    def __init__(self) -> None:
        self._queue = TriageQueue()

    def run(self) -> None:
        try:
            while True:
                print("\n1. Añadir paciente")
                print("2. Llamar al siguiente paciente")
                print("3. Ver cola")
                print("4. Ver estadísticas")
                print("5. Salir")
                choice = input("Elige una opción: ").strip()

                if choice == "1":
                    self._add_patient()
                elif choice == "2":
                    self._call_next()
                elif choice == "3":
                    self._show_queue()
                elif choice == "4":
                    self._show_stats()
                elif choice == "5":
                    print("Hasta luego.")
                    return
                else:
                    print("Opción inválida. Elige un número del 1 al 5.")
        except (EOFError, KeyboardInterrupt):
            print("\nEntrada finalizada. Hasta luego.")

    def _add_patient(self) -> None:
        while True:
            name = input("Nombre del paciente: ").strip()
            if name:
                break
            print("El nombre no puede estar vacío.")

        while True:
            level_input = input("Nivel de triaje (1: crítico, 2: urgente, 3: estándar): ")
            try:
                level = int(level_input)
            except ValueError:
                print("El nivel de triaje debe ser un entero entre 1 y 3.")
                continue
            try:
                patient = Patient(name, level)
            except ValueError as error:
                print(error)
                continue
            self._queue.enqueue(patient)
            print(f"Paciente añadido: {patient.name}.")
            return

    def _call_next(self) -> None:
        try:
            patient = self._queue.dequeue()
        except IndexError as error:
            print(error)
            return
        print(f"Siguiente paciente: {self._format_patient(patient)}")

    def _show_queue(self) -> None:
        patients = self._queue.list_queue()
        if not patients:
            print("No hay pacientes en la cola.")
            return
        print("Pacientes en orden de atención:")
        for patient in patients:
            print(self._format_patient(patient))

    def _show_stats(self) -> None:
        print("Pacientes en espera por nivel:")
        for level, total in self._queue.stats().items():
            print(f"Nivel {level}: {total}")

    @staticmethod
    def _format_patient(patient: Patient) -> str:
        return (
            f"{patient.name} | Nivel {patient.triage_level}"
            f" | Llegada: {patient.arrived_at.isoformat()}"
        )


def main() -> None:
    TriageCLI().run()


if __name__ == "__main__":
    main()