"""Unit tests for the pure parts (no mic, no network, no macOS needed).

Run from office-voice-inbox/:  python3 -m unittest discover tests
"""

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_inbox import inbox, priority, state  # noqa: E402
from voice_inbox.config import Config, _key_from_apis_md, _load_env_file  # noqa: E402


class PriorityTests(unittest.TestCase):
    def test_cues_fire(self):
        for text in [
            "Kyle, remind me about the elders meeting",
            "kyle note we need to fix the parking sign",
            "and that's a task for tomorrow",
            "and thats a task",
            "That’s a task, by the way",  # curly apostrophe from AssemblyAI
            "put that on the list please",
            "PUT THAT ON THE LIST",
        ]:
            self.assertTrue(priority.is_priority(text), text)

    def test_non_cues_do_not_fire(self):
        for text in [
            "the kyleman conference is in October",  # no bare-word match inside words
            "that is a task for someone",
            "put it on the list",
            "",
        ]:
            self.assertFalse(priority.is_priority(text), text)


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(home=Path(self.tmp.name))
        self.cfg.ensure_dirs()

    def tearDown(self):
        self.tmp.cleanup()

    def test_day_key_uses_chicago_time(self):
        # 03:30 UTC on the 2nd is still 22:30 CDT on the 1st.
        dt = datetime(2026, 8, 2, 3, 30, tzinfo=timezone.utc)
        self.assertEqual(inbox.day_key(self.cfg, dt), "2026-08-01")

    def test_entry_shape(self):
        dt = datetime(2026, 8, 22, 14, 41, tzinfo=timezone.utc)  # 09:41 CDT
        entry = inbox.format_entry(self.cfg, dt, "buy stamps", priority=False)
        self.assertEqual(entry, "## 09:41 CT\nbuy stamps\n\n")
        entry = inbox.format_entry(self.cfg, dt, "Kyle note buy stamps", priority=True)
        self.assertEqual(entry, "## 09:41 CT\n[PRIORITY]\nKyle note buy stamps\n\n")

    def test_append_only(self):
        day = "2026-08-22"
        inbox.append_local(self.cfg, day, "## 09:00 CT\nfirst\n\n")
        path = inbox.append_local(self.cfg, day, "## 09:05 CT\nsecond\n\n")
        self.assertEqual(path.name, "2026-08-22 Office Voice Inbox.md")
        self.assertEqual(
            path.read_text(), "## 09:00 CT\nfirst\n\n## 09:05 CT\nsecond\n\n"
        )


class StateTests(unittest.TestCase):
    def test_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            self.assertTrue(state.is_capturing(path))  # missing file -> defaults on
            state.write_state(path, muted=True)
            self.assertFalse(state.is_capturing(path))
            state.write_state(path, muted=False)
            state.write_state(path, listening=False)
            self.assertFalse(state.is_capturing(path))
            state.write_state(path, listening=True)
            self.assertTrue(state.is_capturing(path))


class ConfigTests(unittest.TestCase):
    def test_env_file_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("# comment\nFOO=bar\nQUOTED='x y'\n\nBAD LINE\n")
            self.assertEqual(
                _load_env_file(env), {"FOO": "bar", "QUOTED": "x y"}
            )

    def test_apis_md_key_extraction_without_printing(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "APIs.md"
            md.write_text(
                "# APIs\n\n## AssemblyAI\n"
                "key: abcdef0123456789abcdef0123456789\n\n"
                "## Other\nnope\n"
            )
            self.assertEqual(
                _key_from_apis_md(md), "abcdef0123456789abcdef0123456789"
            )
            self.assertIsNone(_key_from_apis_md(Path(tmp) / "missing.md"))


if __name__ == "__main__":
    unittest.main()
