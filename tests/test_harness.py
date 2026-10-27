"""Contratos puros; validação não depende de IA ou do banco."""
from unittest import TestCase

from agentic_core.harness import get_flow, knowledge_bundle, validate_contract


class HarnessContractTests(TestCase):
    def test_flow_copies_do_not_mutate_the_catalog(self):
        stages = get_flow("coding")
        stages[0]["title"] = "corrompido"
        self.assertEqual(get_flow("coding")[0]["key"], "intake")
        self.assertNotEqual(get_flow("coding")[0]["title"], "corrompido")

    def test_bundle_is_stable_and_does_not_claim_domain_skills_are_installed(self):
        self.assertEqual(knowledge_bundle()["digest"], knowledge_bundle()["digest"])
        self.assertIn("referências", knowledge_bundle()["distribution"])

    def test_contract_rejects_arbitrary_executors_and_unknown_fields(self):
        for payload in ({"execution_mode": "shell"}, {"command": "whoami"}, {"stack": [123]}):
            with self.assertRaises(ValueError):
                validate_contract(payload)

    def test_validation_commands_remain_declarative(self):
        contract = validate_contract({"validation_commands": ["python manage.py check"], "execution_mode": "read_only"})
        self.assertEqual(contract["validation_commands"], ["python manage.py check"])
        self.assertEqual(contract["execution_mode"], "read_only")
