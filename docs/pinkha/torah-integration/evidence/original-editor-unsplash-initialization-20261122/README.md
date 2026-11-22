# Original Unsplash initializer compiler repair

Run [44997870962](https://github.com/davidpovarsky/anytype-swift/actions/runs/44997870962), attempt 1, built frozen producer568d69f55a4b1b1bc318b8ee20144c720c8c16a5 and failed in actual Swift compilation. Its xcodebuild ran07:22:53.914–07:37:15.301 UTC, exited65 and did not time out. The sole attributed source error is UnsplashItemsViewModel.swift:33:30: injected unsplashService is read through self while documentWriteOwner is still uninitialized. A separate corrupted-JSON driver line has no source attribution; its cause is not inferred.

The full original artifact, one-download/hash/CRC receipt, source equality,221 passing source controls, original command, macro trust restoration and terminal sole observer are retained under failed-568d. This is not a qualified framework distribution.

## Exact repair

Only the order of two assignments changes. The original documentWriteOwner let is initialized before the pre-existing self.unsplashService = unsplashService wrapped-property read/set. The original callback assignment, injection identity, search, subscription, publication guards, tasks, nil legacy path and service wrapper remain unchanged.

Immutable upstreamd857b23e confirms the wrapped-property self-assignment was already present. The actual locked Factory revision8ca11a7bd1ede031e8e6d7a912bb116e2e43961b resolves Injected on initialization; its get/set only returns and replaces that stored dependency. Its complete original source and Git blob proof are retained. No alternate dependency is created by this repair.

## New validation

The complete candidate parsed once. A bounded emit-object control compiled the complete projected old ViewModel and reproduced exactly the same uninitialized-self diagnostic, with no extra error. The candidate then compiled and ran one new serialized genuine Swift Testing case: original injected identity and one initial resolution, exact stored Owner and callback item, unchanged original wrapper routing, and the default nil-owner legacy path.

The full actual Injected<T> declaration, complete ViewModel bodies, original value/protocol and DocumentOwnedUnsplashService are retained. External imports are projected for one-module compilation, with two read-only identity accessors. Factory reference/container resolution, Combine/UI, backend and Owner are explicit portable probes. This does not qualify full Factory, Combine, native requests, the actual Owner/runtime, UI, editor or Apple modules. The recorded same-toolchain module cache is reused without replaying an earlier target or assertion.

One new bounded static discovery examined the30 source files mentioning documentWriteOwner and the7 that also use Injected/LazyInjected. The observed Unsplash line is the sole exact injected self-assignment candidate. This is static discovery of the specific new pattern, not exhaustive compiler certification or a repeat of the prior audits.

All original51 package pins and scoped macro trust preparation remain unchanged. The separate Participant/Space composition and metadata branches are not included. The next real Apple framework build, external import, resource runtime and subsequent original editor consumer acceptance remain required.
