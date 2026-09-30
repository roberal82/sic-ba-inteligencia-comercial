import tempfile
import unittest
from pathlib import Path

from src.observability.log import RunLogEntry, RunLogState, RunLogger, SecretLikeFieldError


class RunLoggerTests(unittest.TestCase):
    def test_log_entries_are_appended_as_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = RunLogger(Path(tmp) / "logs" / "run_log.jsonl")
            logger.log(
                RunLogEntry(
                    run_id="run-1",
                    environment="staging",
                    actor="claude-builder",
                    commit_sha="deadbeef",
                    operation="writer.apply",
                    gate="L4",
                    result=RunLogState.SUCCESS,
                    duration_s=1.23,
                )
            )
            logger.log(
                RunLogEntry(
                    run_id="run-2",
                    environment="staging",
                    actor="claude-builder",
                    commit_sha="deadbeef",
                    operation="writer.apply",
                    gate="L4",
                    result=RunLogState.BLOCKED,
                    duration_s=0.1,
                    error="L4 no está en PASS",
                )
            )
            rows = logger.read_all()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["run_id"], "run-1")
            self.assertEqual(rows[1]["result"], "BLOCKED")
            self.assertIn("timestamp", rows[0])

    def test_secret_like_field_names_are_rejected(self):
        with self.assertRaises(SecretLikeFieldError):
            RunLogEntry(
                run_id="run-3",
                environment="staging",
                actor="claude-builder",
                commit_sha="deadbeef",
                operation="writer.apply",
                gate="password=hunter2",
                result=RunLogState.SUCCESS,
                duration_s=0.1,
            )

    def test_secret_like_source_hash_keys_are_rejected(self):
        with self.assertRaises(SecretLikeFieldError):
            RunLogEntry(
                run_id="run-4",
                environment="staging",
                actor="claude-builder",
                commit_sha="deadbeef",
                operation="writer.apply",
                gate="L4",
                result=RunLogState.SUCCESS,
                duration_s=0.1,
                source_hashes={"api_key": "abc"},
            )


if __name__ == "__main__":
    unittest.main()
