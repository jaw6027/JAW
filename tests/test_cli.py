"""Exercise the public command-line behavior."""

import subprocess
import sys
import unittest


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "jaw", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_default_greeting(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Hello, world!\n")

    def test_custom_greeting(self):
        result = self.run_cli("--name", "Jeremy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Hello, Jeremy!\n")

    def test_unknown_argument_is_rejected(self):
        result = self.run_cli("--unknown")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
