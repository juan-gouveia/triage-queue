import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from triage_queue import Patient


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


if __name__ == "__main__":
    unittest.main()
