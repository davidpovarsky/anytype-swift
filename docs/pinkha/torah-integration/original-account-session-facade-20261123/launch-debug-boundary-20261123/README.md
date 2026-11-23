# Embedded launch debug presentation boundary

The actual original LaunchView exposes both private and public debug administration. The original account-session facade uses that view before an Auth caller exists, so a nullable-caller restriction cannot establish this boundary. Both already-embedded facade callsites now pass the exact immutable false presentation option. This composes with the separately reviewed LaunchView default-true standalone implementation and the embedded ApplicationCoordinator initializer.

Only two call expressions changed. Account lifetime, source ownership, real close/drain, UI layout and project membership remain byte-identical. The earlier predicate controls retain their original scope and were not replayed; this source-only child is not an independently buildable SDK until composed with the reviewed Launch implementation.
