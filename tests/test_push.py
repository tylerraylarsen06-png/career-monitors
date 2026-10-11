"""Offline tests for the ntfy.sh phone push and its wiring in run.py.
No network: requests.post and the page fetch are patched out.

    python3 -m unittest discover tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import digest  # noqa: E402
import run  # noqa: E402
from monitors import common  # noqa: E402
from monitors.common import WatchOutcome  # noqa: E402


def outcome(name: str = "JPMorgan Programs", url: str = "https://example.com/jpm") -> WatchOutcome:
    return WatchOutcome(slug="jpm", name=name, url=url, status="changed",
                        old_text="old", new_text="new")


class SendPushTest(unittest.TestCase):
    def test_skips_without_topic(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("digest.requests.post") as post:
            digest.send_push([outcome()])
        post.assert_not_called()

    def test_skips_without_changes(self):
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "t"}), \
                mock.patch("digest.requests.post") as post:
            digest.send_push([])
        post.assert_not_called()

    def test_posts_one_message_per_run(self):
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "my-topic"}), \
                mock.patch("digest.requests.post") as post:
            digest.send_push([outcome("A", "https://a.test"), outcome("B", "https://b.test")])
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/my-topic"))
        self.assertEqual(kwargs["headers"]["Title"], "2 monitors changed")
        self.assertNotIn("Click", kwargs["headers"])
        body = kwargs["data"].decode("utf-8")
        self.assertIn("A: https://a.test", body)
        self.assertIn("B: https://b.test", body)

    def test_uses_gemini_summary_without_markdown(self):
        title, body = digest.build_push([outcome()], "**JPM - applications open: apply.**")
        self.assertEqual(title, "1 monitor changed")
        self.assertEqual(body, "JPM - applications open: apply.")

    def test_low_priority_when_not_urgent(self):
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "t"}), \
                mock.patch("digest.requests.post") as post:
            digest.send_push([outcome()], urgent=False)
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Priority"], "low")
        self.assertEqual(headers["Click"], "https://example.com/jpm")

    def test_long_body_is_capped(self):
        _, body = digest.build_push([outcome()], "x" * 10_000)
        self.assertLessEqual(len(body), digest.NTFY_LIMIT)


class RunWiringTest(unittest.TestCase):
    """Two full offline runs of run.main(): a baseline, then a change.
    Expect exactly one push on the second run and none on the first."""

    def test_change_triggers_one_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            state_dir = Path(tmp) / "state"
            config_dir.mkdir()
            (config_dir / "jpmorgan.yaml").write_text(
                'name: "JPMorgan Careers"\nurl: "https://example.com/jpm"\ntype: html\n'
            )
            pages = iter(["page text version one", "page text version two"])
            env = {"NTFY_TOPIC": "t"}
            with mock.patch.object(run, "CONFIG_DIR", config_dir), \
                    mock.patch.object(run, "STATE_DIR", state_dir), \
                    mock.patch.object(common, "STATE_DIR", state_dir), \
                    mock.patch.object(run, "check_one", side_effect=lambda cfg: next(pages)), \
                    mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch("digest.requests.post") as post:
                self.assertEqual(run.main(), 0)
                post.assert_not_called()
                self.assertEqual(run.main(), 0)
            # No DISCORD_WEBHOOK_URL and no GEMINI_API_KEY: only the push goes out.
            post.assert_called_once()
            self.assertIn("JPMorgan Careers: https://example.com/jpm",
                          post.call_args.kwargs["data"].decode("utf-8"))
            self.assertEqual(post.call_args.kwargs["headers"]["Priority"], "high")


if __name__ == "__main__":
    unittest.main()
