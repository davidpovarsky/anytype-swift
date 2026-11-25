# Dedicated Mac Python bootstrap

The first real Scaleway SDK run, 45420400433/1 at 63041f6, failed before any product restore, build, test or owned simulator creation. The macOS setup-python distribution requires the fixed /Users/runner/hostedtoolcache prefix, which the m1 runner cannot create. Its cleanup then fell back to Apple Python 3.9 and could not import the controller. The original log is retained, with its digest in review.json.

The machine already has native ARM64 Homebrew Python 3.12.16. The scoped Mac workflows now verify Python 3.12, arm64 and Darwin, then append its actual generic-python bin directory to the official GITHUB_PATH environment file. No privilege, tool-cache marker, test admission or simulated GitHub execution context is introduced. The conditional coherent workflow retains setup-python for all other lanes. Live SDK and Page source manifest rows bind the changed workflow bytes.

The single Mac probe imported the existing SDK controller with this interpreter successfully. It is an environment check and carries no product-test or acceptance credit. A fresh real Actions SDK execution remains required.
