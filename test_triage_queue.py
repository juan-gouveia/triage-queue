import threading
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import patch

from triage_queue import EmptyQueueError, Patient, TriageCLI, TriageQueue


class PatientTests(unittest.TestCase):
    def test_valid_levels_and_automatic_arrival_time(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                before = datetime.now(timezone.utc)
                patient = Patient("Ana", level)
                after = datetime.now(timezone.utc)
                self.assertEqual(patient.name, "Ana")
                self.assertEqual(patient.triage_level, level)
                self.assertLessEqual(before, patient.arrived_at)
                self.assertLessEqual(patient.arrived_at, after)

    def test_explicit_arrival_time_is_preserved(self):
        arrival = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(Patient("Ana", 1, arrival).arrived_at, arrival)

    def test_invalid_levels_are_rejected(self):
        for level in (0, 4, -1, 1.0, "1", True, None):
            with self.subTest(level=level):
                with self.assertRaisesRegex(ValueError, "nivel de triaje"):
                    Patient("Ana", level)

    def test_invalid_names_are_rejected(self):
        for name in ("", "   ", None, 123):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "nombre"):
                    Patient(name, 1)

    def test_invalid_arrival_times_are_rejected(self):
        for arrival in (datetime(2026, 1, 1), "2026-01-01", None):
            with self.subTest(arrival=arrival):
                with self.assertRaisesRegex(ValueError, "zona horaria"):
                    Patient("Ana", 1, arrival)

    def test_patient_cannot_be_modified_after_creation(self):
        patient = Patient("Ana", 1)
        with self.assertRaises(FrozenInstanceError):
            patient.triage_level = 2


class TriageQueueTests(unittest.TestCase):
    def test_priority_and_arrival_order(self):
        queue = TriageQueue()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        standard = Patient("Estándar", 3, start)
        urgent = Patient("Urgente", 2, start)
        later = Patient("Crítico posterior", 1, start + timedelta(seconds=1))
        earlier = Patient("Crítico anterior", 1, start)
        for patient in (standard, urgent, later, earlier):
            queue.enqueue(patient)

        self.assertEqual(
            [queue.dequeue() for _ in range(4)],
            [earlier, later, urgent, standard],
        )

    def test_equal_arrival_times_keep_enqueue_order(self):
        queue = TriageQueue()
        arrival = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = Patient("Primero", 2, arrival)
        second = Patient("Segundo", 2, arrival)
        queue.enqueue(first)
        queue.enqueue(second)
        self.assertEqual(queue.dequeue(), first)
        self.assertEqual(queue.dequeue(), second)

    def test_listing_peeking_and_stats_do_not_remove_patients(self):
        queue = TriageQueue()
        standard = Patient("Estándar", 3)
        critical = Patient("Crítico", 1)
        queue.enqueue(standard)
        queue.enqueue(critical)

        self.assertEqual(queue.peek(), critical)
        self.assertEqual(queue.list_queue(), [critical, standard])
        self.assertEqual(queue.stats(), {1: 1, 2: 0, 3: 1})
        self.assertEqual(queue.dequeue(), critical)
        self.assertEqual(queue.stats(), {1: 0, 2: 0, 3: 1})
        self.assertEqual(queue.dequeue(), standard)
        self.assertEqual(queue.list_queue(), [])
        self.assertEqual(queue.stats(), {1: 0, 2: 0, 3: 0})

    def test_empty_queue_raises_descriptive_errors(self):
        queue = TriageQueue()
        for operation in (queue.dequeue, queue.peek):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(IndexError, "No hay pacientes"):
                    operation()

    def test_times_in_different_zones_are_ordered_by_instant(self):
        queue = TriageQueue()
        first = Patient("Primero", 1, datetime(2026, 1, 1, 9, tzinfo=timezone.utc))
        second = Patient(
            "Segundo", 1, datetime(2026, 1, 1, 11, tzinfo=timezone(timedelta(hours=1)))
        )
        queue.enqueue(second)
        queue.enqueue(first)
        self.assertEqual(queue.list_queue(), [first, second])

    def test_naive_arrival_is_rejected_without_changing_queue(self):
        queue = TriageQueue()
        existing = Patient("Existente", 1)
        queue.enqueue(existing)
        with self.assertRaisesRegex(ValueError, "zona horaria"):
            queue.enqueue(Patient("Sin zona", 1, datetime(2026, 1, 1)))
        self.assertEqual(queue.list_queue(), [existing])

    def test_critical_arrival_during_processing_preempts_waiting_patients(self):
        queue = TriageQueue()
        arrival = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = Patient("Primer urgente", 2, arrival)
        second = Patient("Segundo urgente", 2, arrival)
        standard = Patient("Estándar", 3, arrival)
        critical = Patient("Crítico", 1, arrival + timedelta(seconds=1))
        for patient in (first, second, standard):
            queue.enqueue(patient)

        self.assertEqual(queue.dequeue(), first)
        queue.enqueue(critical)
        self.assertEqual(queue.peek(), critical)
        self.assertEqual(queue.list_queue(), [critical, second, standard])
        self.assertEqual(queue.stats(), {1: 1, 2: 1, 3: 1})
        self.assertEqual(
            [queue.dequeue() for _ in range(3)], [critical, second, standard]
        )

    def test_empty_queue_error_is_specific(self):
        queue = TriageQueue()
        for operation in (queue.dequeue, queue.peek):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(EmptyQueueError):
                    operation()

    def test_only_patients_can_be_enqueued(self):
        queue = TriageQueue()
        with self.assertRaises(TypeError):
            queue.enqueue(("Ana", 1))
        self.assertEqual(queue.list_queue(), [])

    def test_concurrent_workers_never_claim_the_same_patient(self):
        queue = TriageQueue()
        total = 2000
        patients = [Patient(f"P{i}", i % 3 + 1) for i in range(total)]
        claimed: list[Patient] = []
        claimed_lock = threading.Lock()
        producers_done = threading.Event()

        def produce(chunk):
            for patient in chunk:
                queue.enqueue(patient)

        def consume():
            while True:
                try:
                    patient = queue.dequeue()
                except EmptyQueueError:
                    if producers_done.is_set() and not queue.list_queue():
                        return
                    continue
                with claimed_lock:
                    claimed.append(patient)

        producers = [
            threading.Thread(target=produce, args=(patients[i::4],)) for i in range(4)
        ]
        consumers = [threading.Thread(target=consume) for _ in range(4)]
        for thread in producers + consumers:
            thread.start()
        for thread in producers:
            thread.join()
        producers_done.set()
        for thread in consumers:
            thread.join()

        self.assertEqual(len(claimed), total)
        self.assertEqual({p.name for p in claimed}, {p.name for p in patients})

    def test_queue_remains_usable_after_empty_operations(self):
        queue = TriageQueue()
        with self.assertRaises(IndexError):
            queue.peek()
        with self.assertRaises(IndexError):
            queue.dequeue()

        patient = Patient("Ana", 2)
        queue.enqueue(patient)
        self.assertEqual(queue.peek(), patient)
        self.assertEqual(queue.dequeue(), patient)
        self.assertEqual(queue.stats(), {1: 0, 2: 0, 3: 0})


class TriageCLITests(unittest.TestCase):
    @staticmethod
    def _run_cli(inputs, queue=None):
        """Ejecuta la CLI con las entradas dadas y devuelve todo lo impreso."""
        with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=StringIO) as output:
            TriageCLI(queue).run()
        return output.getvalue()

    def test_invalid_menu_option_returns_to_menu(self):
        text = self._run_cli(["x", "9", "5"])
        self.assertEqual(text.count("Opción inválida"), 2)
        self.assertIn("Hasta luego.", text)

    def test_invalid_name_and_level_are_asked_again(self):
        queue = TriageQueue()
        text = self._run_cli(["1", "", "   ", "Ana", "no", "4", "3", "5"], queue)
        self.assertEqual(text.count("El nombre no puede estar vacío"), 2)
        self.assertEqual(text.count("El nivel de triaje debe ser"), 2)
        self.assertIn("Paciente añadido: Ana.", text)
        self.assertEqual([(p.name, p.triage_level) for p in queue.list_queue()], [("Ana", 3)])

    def test_empty_queue_is_reported_without_crashing(self):
        text = self._run_cli(["2", "3", "5"])
        self.assertEqual(text.count("No hay pacientes en la cola."), 2)
        self.assertIn("Hasta luego.", text)

    def test_queue_and_stats_follow_priority(self):
        inputs = ["1", "Ana", "3", "1", "Luis", "1", "4", "3", "2", "2", "5"]
        text = self._run_cli(inputs)
        self.assertIn("Nivel 1 (Crítico): 1", text)
        self.assertIn("Nivel 2 (Urgente): 0", text)
        self.assertIn("Nivel 3 (Estándar): 1", text)
        listing = text.split("Pacientes en orden de atención:")[1].split("\n1. Añadir paciente")[0]
        self.assertIn("1. Luis | Nivel 1 (Crítico)", listing)
        self.assertIn("2. Ana | Nivel 3 (Estándar)", listing)
        self.assertLess(text.index("Siguiente paciente: Luis"), text.index("Siguiente paciente: Ana"))

    def test_cli_uses_injected_queue(self):
        queue = TriageQueue()
        queue.enqueue(Patient("Eva", 1))
        text = self._run_cli(["3", "2", "5"], queue)
        self.assertIn("1. Eva | Nivel 1 (Crítico)", text)
        self.assertIn("Siguiente paciente: Eva", text)
        self.assertEqual(queue.list_queue(), [])

    def test_eof_exits_cleanly_during_patient_registration(self):
        text = self._run_cli(["1", EOFError])
        self.assertIn("Entrada finalizada", text)


if __name__ == "__main__":
    unittest.main()
