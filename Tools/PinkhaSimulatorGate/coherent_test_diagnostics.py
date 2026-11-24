"""Installed Xcode27 policy for coherent current-run failure finalization.

This changes automatic sysdiagnose/logarchive collection only. XCTest
assertions, allowances and explicit keepAlways attachments remain intact.
"""


def never(argv):
    command = list(argv)
    if not command or command[0].split("/")[-1] != "xcodebuild" or "test-without-building" not in command:
        return command
    if "-enumerate-tests" in command:
        return command
    if "-collect-test-diagnostics" in command:
        index = command.index("-collect-test-diagnostics")
        if command.count("-collect-test-diagnostics") != 1 or command[index + 1:index + 2] != ["never"]:
            raise ValueError("Conflicting coherent test diagnostic policy")
        return command
    return [*command, "-collect-test-diagnostics", "never"]


class Pair:
    """Scope the policy to the real commands of one fresh coherent execution."""
    def __init__(self, original):
        self.original = original

    def __getattr__(self, name):
        return getattr(self.original, name)

    def run_logged(self, argv, *args, **kwargs):
        return self.original.run_logged(never(argv), *args, **kwargs)
