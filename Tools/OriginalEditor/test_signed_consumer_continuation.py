"""Regress the actual stderr-only Xcode27 help, without executing Apple tools."""
from pathlib import Path
import unittest
from consumer_failure_capture import combine_launch_help

PACKET = Path(__file__).resolve().parents[2] / 'docs/pinkha/torah-integration/evidence/original-editor-signed-consumer-20261123'


class LaunchHelpStreams(unittest.TestCase):
    def setUp(self):
        self.help = (PACKET / 'actual-simctl-launch-help.stderr.log').read_text()

    def test_actual_stderr_help_is_admitted_with_empty_stdout(self):
        stdout = (PACKET / 'actual-simctl-launch-help.stdout.log').read_text()
        self.assertEqual(stdout, '')
        self.assertIn('--stdout=<path>', combine_launch_help(stdout, self.help))
        self.assertIn('--stderr=<path>', combine_launch_help(stdout, self.help))

    def test_stdout_help_remains_supported(self):
        self.assertIn(self.help, combine_launch_help(self.help, ''))

    def test_missing_output_option_still_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'does not advertise'):
            combine_launch_help('', self.help.replace('--stderr', '--unavailable'))

    def test_oversized_help_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'bounded'):
            combine_launch_help(self.help, 'x' * 65537)


if __name__ == '__main__':
    unittest.main()
