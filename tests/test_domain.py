import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.domain import completion_percent, normalize_stage, proposal_conversion

class DomainTests(unittest.TestCase):
    def test_completion(self): self.assertEqual(completion_percent(3, 4), 75)
    def test_empty_total(self): self.assertEqual(completion_percent(0, 0), 0)
    def test_completion_is_bounded(self): self.assertEqual(completion_percent(12, 10), 100)
    def test_conversion(self): self.assertEqual(proposal_conversion(2, 5), 40)
    def test_normalize_stage(self): self.assertEqual(normalize_stage(" Proposta "), "proposta")
    def test_invalid_stage(self):
        with self.assertRaises(ValueError): normalize_stage("inexistente")

if __name__ == "__main__":
    unittest.main()
