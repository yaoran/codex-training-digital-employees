from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", MODULE_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class SafeReadTests(unittest.TestCase):
    def test_normal_utf8_file_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "input.json"
            path.write_text('{"ok": true}', encoding="utf-8")
            self.assertEqual(validator.load_json(path, root=root), {"ok": True})

    def test_outside_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ValueError, "超出仓库范围"):
                validator.safe_repo_path(Path(outside), root=Path(directory), kind="directory")

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "outside.json"
            target.write_text('{"outside": true}', encoding="utf-8")
            link = root / "input.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "不允许符号链接"):
                validator.load_json(link, root=root)

    def test_oversized_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "large.json"
            path.write_text(" " * (validator.MAX_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "超过"):
                validator.load_json(path, root=root)

    def test_directory_is_rejected_as_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "普通文件"):
                validator.load_json(root, root=root)

    def test_current_repository_passes(self) -> None:
        self.assertEqual(validator.validate(), [])


if __name__ == "__main__":
    unittest.main()
