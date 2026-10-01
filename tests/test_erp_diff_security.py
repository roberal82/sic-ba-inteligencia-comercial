"""Tests de seguridad: escritura atómica, path traversal y aislamiento de output_dir."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.erp_diff_engine.security import (
    EngineInputError,
    EngineSecurityError,
    atomic_write_text,
    prepare_output_dir,
    require_existing_file,
    safe_output_path,
    sha256_file,
)


class RequireExistingFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_raises_engine_input_error(self) -> None:
        with self.assertRaises(EngineInputError):
            require_existing_file(self.base_dir / "no_existe.xlsx", "BASE")

    def test_directory_is_rejected(self) -> None:
        directory = self.base_dir / "carpeta"
        directory.mkdir()
        with self.assertRaises(EngineInputError):
            require_existing_file(directory, "BASE")

    def test_existing_file_is_accepted(self) -> None:
        file_path = self.base_dir / "archivo.txt"
        file_path.write_text("contenido", encoding="utf-8")
        resolved = require_existing_file(file_path, "BASE")
        self.assertTrue(resolved.exists())


class SafeOutputPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.output_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_plain_filename_is_allowed(self) -> None:
        path = safe_output_path(self.output_dir, "diff_summary.json")
        self.assertEqual(path.parent, self.output_dir)

    def test_parent_traversal_is_blocked(self) -> None:
        with self.assertRaises(EngineSecurityError):
            safe_output_path(self.output_dir, "../escape.json")

    def test_absolute_path_is_blocked(self) -> None:
        escape = str(self.output_dir.parent / "escape.json")
        with self.assertRaises(EngineSecurityError):
            safe_output_path(self.output_dir, escape)


class PrepareOutputDirTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_creates_output_dir_when_missing(self) -> None:
        output_dir = self.root / "salida"
        resolved = prepare_output_dir(output_dir)
        self.assertTrue(resolved.exists())

    def test_rejects_output_dir_equal_to_input(self) -> None:
        shared = self.root / "compartido"
        shared.mkdir()
        input_file = shared / "BASE.xlsx"
        input_file.write_text("x", encoding="utf-8")
        with self.assertRaises(EngineSecurityError):
            prepare_output_dir(shared, input_file.parent)

    def test_rejects_output_dir_ancestor_of_input(self) -> None:
        output_dir = self.root / "salida"
        nested_input = output_dir / "subcarpeta" / "BASE.xlsx"
        nested_input.parent.mkdir(parents=True)
        nested_input.write_text("x", encoding="utf-8")
        with self.assertRaises(EngineSecurityError):
            prepare_output_dir(output_dir, nested_input)


class AtomicWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.output_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_write_then_overwrite_leaves_no_tmp_files(self) -> None:
        target = self.output_dir / "reporte.json"
        atomic_write_text(target, "{}")
        atomic_write_text(target, '{"a": 1}')
        self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 1}')
        leftovers = [p for p in self.output_dir.iterdir() if p.name != "reporte.json"]
        self.assertEqual(leftovers, [])


class Sha256Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sha256_is_deterministic(self) -> None:
        file_path = self.base_dir / "a.txt"
        file_path.write_bytes(b"contenido de prueba")
        self.assertEqual(sha256_file(file_path), sha256_file(file_path))

    def test_sha256_changes_with_content(self) -> None:
        file_path = self.base_dir / "a.txt"
        file_path.write_bytes(b"contenido 1")
        first = sha256_file(file_path)
        file_path.write_bytes(b"contenido 2")
        second = sha256_file(file_path)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
