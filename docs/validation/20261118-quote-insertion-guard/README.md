# Quote and external-drop action lifetime repair

The previous Inspector insertion callback did not use its existing action-lifetime guard. External item-provider decoding also looked up the view model after loading, and a document-wide payload set prevented later intentional drops of the same source.

The controller now captures a weak, document-bound insertion action before decoding. Each drop has one local claim, and a later gesture has a separate claim. Inspector actions additionally bind their original presentation epoch and selection. Leaving and reopening a document cannot revive an older action. The native view model checks current block and property editing permission before dispatch.

After a block response, metadata is authorized again. The native association repository revalidates after its queued read and propagates caller cancellation into the serialized operation. If the block has already committed, the code preserves the text and reports an uncertain partial insertion in the still-current presentation. An old completion cannot replace the new document or Inspector status.

Ten Swift test functions cover twelve cases, with explicit suspended block/native reads rather than timing sleeps: stale document and Inspector callbacks, revoked authority, per-gesture duplication, intentional repeat insertion, independent Inspector dismissal, partial commits, cancellation and confirmed canonical metadata. Existing probe conformances were updated for the guarded add contract.

The recorded local check parsed all ten changed/new Swift files in Swift 5 mode and preserved every existing Hebrew code point. Independent source review found no blocking issue. This is syntax/source validation only; Apple compilation, execution of these tests, real drag/drop, caret and Undo acceptance remain pending. The local authorization check does not claim atomic ACL enforcement at the later native commit.
