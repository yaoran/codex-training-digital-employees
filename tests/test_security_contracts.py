from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-training-digital-employees"
CHECKER_PATH = PLUGIN / "scripts" / "check_html_safety.py"
SPEC = importlib.util.spec_from_file_location("check_html_safety", CHECKER_PATH)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


SAFE_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<style>body { color: #222; }</style></head><body>&lt;script&gt;仅作为文本&lt;/script&gt;</body></html>
"""


class SecurityContractTests(unittest.TestCase):
    def test_every_skill_declares_untrusted_input_boundary(self) -> None:
        for skill_file in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
            text = skill_file.read_text(encoding="utf-8")
            self.assertIn("## 不可信输入边界", text, skill_file)
            self.assertIn("不得执行", text, skill_file)

    def test_html_workflows_require_safety_checker_and_csp(self) -> None:
        references = [
            PLUGIN / "skills" / "task-execution-employee" / "references" / "task-package-workflow.md",
            PLUGIN / "skills" / "meeting-minutes-employee" / "references" / "meeting-minutes-workflow.md",
        ]
        for reference in references:
            text = reference.read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", text, reference)
            self.assertIn("check_html_safety.py", text, reference)

    def test_safe_html_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "safe.html"
            path.write_text(SAFE_HTML, encoding="utf-8")
            self.assertEqual(checker.validate_html(path), [])

    def test_embedded_raster_image_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "safe-image.html"
            path.write_text(
                SAFE_HTML.replace("</body>", '<img src="data:image/png;base64,AA==" alt="示例"></body>'),
                encoding="utf-8",
            )
            self.assertEqual(checker.validate_html(path), [])

    def test_active_html_payloads_are_rejected(self) -> None:
        payloads = [
            "<script>alert(1)</script>",
            '<img src="data:image/png;base64,AA" onerror="alert(1)">',
            '<a href="javascript:alert(1)">click</a>',
            '<img src="https://example.com/track.png">',
            '<meta http-equiv="refresh" content="0;url=https://example.com">',
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, payload in enumerate(payloads):
                path = Path(directory) / f"unsafe-{index}.html"
                path.write_text(SAFE_HTML.replace("</body>", f"{payload}</body>"), encoding="utf-8")
                self.assertTrue(checker.validate_html(path), payload)

    def test_csp_and_network_attribute_bypasses_are_rejected(self) -> None:
        csp = (
            '<meta http-equiv="Content-Security-Policy" '
            'content="default-src \'none\'; style-src \'unsafe-inline\'; '
            'img-src data:; base-uri \'none\'; form-action \'none\'">'
        )
        payloads = [
            SAFE_HTML.replace(
                "</body>", '<img srcset="https://example.com/track.png"></body>'
            ),
            SAFE_HTML.replace("img-src data:", "img-src data: https:"),
            SAFE_HTML.replace(csp, "").replace("<body>", f"<body>{csp}"),
            SAFE_HTML.replace("default-src 'none'", "x-default-src 'none'"),
            SAFE_HTML.replace(csp, csp.replace('content="', 'content="default-src https:" content="', 1)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, payload in enumerate(payloads):
                path = Path(directory) / f"csp-bypass-{index}.html"
                path.write_text(payload, encoding="utf-8")
                self.assertTrue(checker.validate_html(path), payload)


if __name__ == "__main__":
    unittest.main()
