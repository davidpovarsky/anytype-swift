# Candidate Page154 publication and visible selection

Status at this source freeze: the new controls have not run. The module sources
will compile in the existing Oracle Swift 6.4.3 ARM64 host composition; the App
files are metadata only there. The distinct Apple producer has established the
actual Page154 header, defined symbol, runtime version and Swift call signature,
but that does not establish an App call or mounted editor behavior.

## Existing evidence retained

Baseline source 55b781591de6d91d680d1190f62a580c3b8d60f7 had two test fixture
compile repairs before the actual 22 methods passed at
fbbfe7100425482e3d9f8b6623bb2d1920f56528. The baseline receipt commit is
65512667b0f3d22d87036c7b78190bdfb6334437. All 695 baseline product source files
were unchanged across those test-only repairs. The original compiler failures,
successful compiled runner/module, fixtures and named events remain preserved.
The actual native Page capture and separate-process reopen receipts stay at
2656284b2670651fa7aa02661024b1fd0b041656 and are not rerun by this change.

## New bounded behavior

The actual native returned ResponseEvent is still published through the existing
Invocation handler. Its owner witness binds the exact serialized event, account,
Space, object and live lifetime generation. EventsListener uses the witness only
around bounded synchronous converter/container state work. No fence lock is held
over subscriber callbacks, asynchronous work or a main-queue wait.

BaseDocument explicitly carries the witness across its existing GCD hop and
rechecks immediately before sync delivery. The two affected editor consumers
carry it across their existing Combine scheduling and recheck native lifetime
plus their current editor/block identity. Other ResponseEvents and ordinary
updates retain the original route. The new wire API does not manufacture an
alternate reducer event.

The editor offers a localized action for a current editable native text selection
with no pending local text edit. Menu construction captures the actual native
lease and exact editor/input binding. Preparation checks current native text and
marks without mutation; only the subsequent explicit confirmation queues one
capture. Cancellation before that action has no native write. Stale selection,
retired generation, changed block, unsupported runtime and uncertain outcomes
fail closed. A queued native operation is never automatically retried.

All feature call sites require both the existing authorized lifetime flag and
the distinct Page154 flag. Default production139 capability remains off. No
PinkhaKit source, schema, protobuf, native154 input or existing139 producer changes.

## Focused control scope

The next selected suite contains 19 Client methods: 8 new methods for read-only
visible preparation, ownership/Unicode checks, exact publication identity,
retirement during publication and an explicitly carried GCD hop, plus the 11
existing Client methods affected by the publication change. The unchanged 11 Wire
methods are retained from the actual baseline pass and will not rerun.

The host checks exercise the exact product fence and client with controlled IO.
They do not compile UIKit, execute the actual App EventsListener reducer, invoke
Lib, or claim mounted editor acceptance. AppCandidateSources.json pins all 15
changed/new App source and localization files for the separate full-App consumer.
The consumer must use the real InvocationMesagesHandler and real opened document;
mounted selection/confirmation still requires its own observed acceptance.

## Known boundaries

Native acceptance remains the explicit-empty Restrictions fixture scope already
documented by the Page154 native receipts. The editor source does not broaden
that guarantee. The new action creates a native text anchor only; a dedicated
reserved-anchor URL navigation route is not introduced here. File migration,
full archive migration and shipping activation are outside this change.

## Independent source review before freeze

The SDK/Apple lane reviewed this authored path without edits or test execution.
It found no demonstrated blocker in the inspected path: the typed plan admits
exactly one blockSetText/marks event; the fenced InfoContainer, mention and
indentation operations stay synchronous and in-memory; subscriber callbacks
occur outside the state lock. BaseDocument carries the fence across GCD and the
two editor consumers capture it before Combine schedules. The actual App source
hashes for this review are in AppCandidateSources.json, whose SHA-256 is
3a28777a1b1b42e027350b3b496a3a020156088b2ce4a7feb0d7651b3e596c57.
This is a structural review only. Apple compilation and mounted UI execution
remain unverified.
