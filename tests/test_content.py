import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study_build", ROOT / "scripts/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ContentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("templates", "assets", "schemas", "content", "scripts"):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ("AGENTS.md", "project.json"):
            shutil.copy2(ROOT / name, self.root / name)
        self.path = self.root / "content/generative-ai.json"
        self.topic = json.loads(self.path.read_text(encoding="utf-8"))
    def tearDown(self):
        self.temp.cleanup()
    def write(self, topic):
        self.path.write_text(json.dumps(topic, ensure_ascii=False), encoding="utf-8")
    def test_unknown_quote_is_rejected(self):
        self.topic["cards"][0]["evidence"] = "這是來源中不存在的句子。"
        self.write(self.topic)
        with self.assertRaisesRegex(build.ContentError, "evidence"):
            build.render_site(self.root)
    def test_wrong_paragraph_is_rejected(self):
        self.topic["cards"][0]["source_id"] = "p2"
        self.write(self.topic)
        with self.assertRaisesRegex(build.ContentError, "evidence"):
            build.render_site(self.root)
    def test_duplicate_order_is_rejected(self):
        self.topic["order"] = 2
        self.write(self.topic)
        with self.assertRaisesRegex(build.ContentError, "duplicate order"):
            build.render_site(self.root)
    def test_missing_required_field_is_rejected(self):
        del self.topic["objectives"]
        self.write(self.topic)
        with self.assertRaisesRegex(build.ContentError, "missing"):
            build.render_site(self.root)
    def test_path_traversal_slug_is_rejected(self):
        self.topic["slug"] = "../escape"
        self.write(self.topic)
        with self.assertRaises(build.ContentError):
            build.render_site(self.root)
    def test_duplicate_section_is_rejected(self):
        self.topic["sections"][1]["id"] = "p1"
        self.write(self.topic)
        with self.assertRaisesRegex(build.ContentError, "duplicate section"):
            build.render_site(self.root)
    def test_malformed_json_is_rejected(self):
        self.path.write_text("{bad", encoding="utf-8")
        with self.assertRaises(build.ContentError):
            build.render_site(self.root)
    def test_text_is_escaped_and_script_cannot_break_out(self):
        self.topic["cards"][0]["question"] = "</script><img src=x onerror=alert(1)>"
        self.topic["sections"][0]["paragraphs"].append("<script>alert('example')</script>")
        self.write(self.topic)
        output, _ = build.render_site(self.root)
        text = output["topics/generative-ai.html"].decode("utf-8")
        self.assertNotIn("<img src=x", text)
        self.assertIn("\\u003c/script\\u003e", text)
        self.assertIn("&lt;script&gt;", text)
    def test_broken_anchor_is_detected(self):
        output, _ = build.render_site(self.root)
        output["index.html"] = output["index.html"].replace(b"#topics", b"#missing-anchor")
        with self.assertRaisesRegex(build.ContentError, "broken anchor"):
            build.check_links(output)
    def test_generated_site_is_deterministic_and_portable(self):
        first, topics = build.render_site(self.root)
        second, _ = build.render_site(self.root)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(topics), 2)
        for name, data in first.items():
            if name.endswith(".html"):
                self.assertNotIn(b'href="/', data)
                self.assertNotIn(b'src="/', data)
                self.assertIn('lang="zh-Hant"', data.decode("utf-8"))
    def test_failed_build_does_not_overwrite_existing_output(self):
        docs = self.root / "docs"
        docs.mkdir()
        sentinel = docs / "index.html"
        sentinel.write_text("KEEP EXISTING OUTPUT", encoding="utf-8")
        self.topic["cards"][0]["evidence"] = "這段文字沒有原文依據。"
        self.write(self.topic)
        result = subprocess.run([sys.executable, str(self.root / "scripts/build.py")], capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "KEEP EXISTING OUTPUT")
    def test_invalid_reference_scheme_is_rejected(self):
        self.topic["references"][0]["url"] = "javascript:alert(1)"
        self.write(self.topic)
        with self.assertRaises(build.ContentError):
            build.render_site(self.root)


if __name__ == "__main__":
    unittest.main()
