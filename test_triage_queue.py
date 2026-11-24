import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from triage_queue import Patient, TriageQueue


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


if __name__ == "__main__":
    unittest.main()
