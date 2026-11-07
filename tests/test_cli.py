"""Offline checks for the full command parser and bulk argument dispatch."""
import contextlib
import io
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from spotify_mcp import cli

COMMANDS = ("now", "search", "devices", "play", "pause", "skip", "prev", "volume", "queue", "transfer",
            "playlists", "get", "artist", "recent", "top", "resolve", "create", "add", "remove",
            "reorder", "rename", "empty", "delete", "like")


class ParserTests(unittest.TestCase):
    def test_help_for_every_command_without_spotify(self):
        for command in (None, *COMMANDS):
            with self.subTest(command=command), mock.patch.object(cli.client, "_request", side_effect=AssertionError("network")):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    with self.assertRaises(SystemExit) as result:
                        cli.main(([command] if command else []) + ["--help"])
                self.assertEqual(result.exception.code, 0)
                self.assertIn("usage:", out.getvalue())
        for command in ("add", "remove", "like"):
            with self.subTest(command=command), contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit): cli.main([command, "--help"])
                self.assertIn("--file", out.getvalue())
                self.assertIn("--stdin", out.getvalue())

    def test_bulk_flags_and_items_reach_mocked_client(self):
        cases = [
            ("playlist_add", ["add", "playlist", "first", "second", "--no-dedupe"],
             ("playlist", ["first", "second"]), {"dedupe": False}),
            ("playlist_remove", ["remove", "playlist", "first", "--confirm"],
             ("playlist", ["first"]), {"confirm": True}),
            ("save_tracks", ["like", "first", "second"], (["first", "second"],), {}),
        ]
        for method, argv, expected_args, expected_kwargs in cases:
            with self.subTest(command=argv[0]), mock.patch.object(cli.client, method, return_value={}) as call:
                with contextlib.redirect_stdout(io.StringIO()): cli.main(argv)
                call.assert_called_once_with(*expected_args, **expected_kwargs)

    def test_file_and_stdin_items_reach_mocked_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = Path(tmp) / "tracks.txt"
            items.write_text("file track\n")
            with mock.patch.object(cli.client, "playlist_add", return_value={}) as call:
                with mock.patch("sys.stdin", io.StringIO("stdin track\n")), contextlib.redirect_stdout(io.StringIO()):
                    cli.main(["add", "playlist", "--file", str(items), "--stdin"])
                call.assert_called_once_with("playlist", ["file track", "stdin track"], dedupe=True)


if __name__ == "__main__":
    unittest.main()
