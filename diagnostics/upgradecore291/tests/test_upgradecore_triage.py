"""Offline synthetic tests; no Docker or CABAL game needed."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "upgrade_triage", Path(__file__).resolve().parent.parent / "Analyze-UpgradeCore-v291.py"
)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)

def sample(case):
    return {"case": case, "read_only": True,
            "status": {"world_observation": "WORLD_PID_STABLE_IN_SAMPLES"},
            "samples": [{"snapshot": {"services": [], "pids": {"WorldSvr_01_01": 12}}}],
            "before": {"files": [], "corefiles": []},
            "after": {"files": [], "corefiles": []},
            "docker_logs": {"matched_lines": []}}

class TriageTests(unittest.TestCase):
    def make(self):
        return {x: sample(x) for x in ("upgrade", "perfect", "force-control")}

    def test_stable_world_does_not_prove_protocol(self):
        trials = {k: triage.classify(v) for k, v in self.make().items()}
        self.assertEqual(triage.interpret(trials)[0], "NEEDS_PROTOCOL_TRACING")

    def test_upgrade_crash(self):
        cases = self.make()
        cases["upgrade"]["after"]["corefiles"] = [
            {"path": "/etc/cabal_etc/core/core.WorldSvr", "mtime": 42.0, "size": 12}]
        trials = {k: triage.classify(v) for k, v in cases.items()}
        self.assertEqual(trials["upgrade"]["new_or_changed_corefiles"], 1)
        self.assertEqual(triage.interpret(trials)[0], "INSPECT_WORLD_CRASH")

    def test_both_failures_have_rejections(self):
        cases = self.make()
        for name in ("upgrade", "perfect"):
            cases[name]["after"]["files"] = [{"matched_lines": ["WorldSvr invalid packet length"]}]
        trials = {k: triage.classify(v) for k, v in cases.items()}
        self.assertEqual(triage.interpret(trials)[0], "NORMAL_UPGRADE_REJECTION_SUSPECTED")

    def test_incomplete_log_data(self):
        cases = self.make()
        cases["perfect"]["after"] = {"error": "CONTAINER_PYTHON_UNAVAILABLE", "corefiles": []}
        trials = {k: triage.classify(v) for k, v in cases.items()}
        self.assertEqual(triage.interpret(trials)[0], "COLLECTION_INCOMPLETE")

    def test_control_crash_is_not_normal_upgrade_specific(self):
        cases = self.make()
        cases["force-control"]["status"]["world_observation"] = "WORLD_PID_CHANGED_RESTART_POSSIBLE"
        trials = {k: triage.classify(v) for k, v in cases.items()}
        self.assertEqual(triage.interpret(trials)[0], "CONTROL_NOT_STABLE")

if __name__ == "__main__":
    unittest.main()
