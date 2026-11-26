# Explicit owned simulator retention

The native UI controller accepts `--retain-owned-simulator` for a bounded diagnostic continuation. It still stops the provider, shuts down only its newly created device, preserves the private native sandbox, verifies all original product inputs and requires the same exact original one-method PASS result. The opt-in path requires the actual device to remain uniquely present in Shutdown state; the default path still requires its absence after its owned deletion. No device-wide cleanup, existing account, source assertion, stage selector, app input or native input changes.

This source review is controller preparation only. It is not a UI acceptance result.
