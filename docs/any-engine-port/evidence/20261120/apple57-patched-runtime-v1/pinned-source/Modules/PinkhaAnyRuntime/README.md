# Embedded Any runtime for iOS

Pins the public Any v0.5.0 XCFramework to its published SHA256 and imports the
real `AnyLib` C archive. The artifact contains arm64 iOS/device and simulator
slices, with minimum iOS 18.4. This package is deliberately separate from the
portable HTTP/domain packages.

`AnyEmbeddedRuntime.shared` serializes ownership of the process-global engine.
The host supplies a dedicated data directory and explicitly chooses a network.
It starts managed mode on an ephemeral literal-loopback port, generates a fresh
random control token for every boot, validates the linked version, and exposes
the engine's structured start errors without deleting or "repairing" user data.

The session makes only the three control request shapes (auth/sign-out/shutdown).
The host owns Keychain storage and account/consent lifecycle. Control tokens do
not authorize data routes. Document operations must be drained before account
switch/stop; this package does not claim an atomic cross-object authorization
fence. Its actor `stopNow` is not a synchronous UIKit expiry callback.

The real-library simulator test checks managed unauthorized startup, health,
control rejection without a token, duplicate-start rejection, fresh token on
restart, graceful stop, and the hard-stop binding. It creates no account and
uses an explicit placeholder network. A passing package test is not full app
or physical iPad acceptance.

Source: anyproto/any `88fae2e5ae7d0f46d6707567a3123081faa8de9a`,
`mobile/ios/anylib.go`, `scripts/build-xcframework.sh`, and
`website/02-quickstart/ios.md`.
