# Follow-up: bind local input to its actual handler

A review of the first shared-editor patch found that a reused content view could
apply the new handler's pending flag to the previous handler's live text. The
configuration now carries ObjectIdentifier(actionHandler) as an equality-sensitive
field. Different handlers force the new owner's text into the reused view. A
same-handler empty-block fork changes block ID without surrendering its input.

A nonnil reset text is explicitly marked as a user replacement. A nil reset is
only a native refresh. New-owner and explicit-replacement rendering ends the old
composition with the CustomTextView delegate disconnected for that synchronous
operation, preventing the superseded buffer from being delivered to the new
handler. Ordinary native echoes retain the shared composition protection.

Queued input now snapshots the composition flag with its text. It never queries
a reused UITextView after suspension. Structural keyboard actions commit a
nonempty deferred local buffer through the same queue before native split/merge,
so successful materialization does not leave an obsolete dirty flag.

Normal TextBlockViewModel.rebind(to:) does not reset forkGeneration. Only the
explicit rebindAfterIdentityUndo(to:) path calls resetEmptyBlockFork(); generation
checks therefore retain a legitimate same-handler native fork.

Two additional UIKit methods (three invocations) cover different pending owners
with and without marked text, equality-sensitive ownership, same-handler fork,
native-echo composition preservation and explicit replacement:
- reusedCellDoesNotPreserveDifferentPendingOwner(composing:) —false,true.
- sameInputOwnerSurvivesForkAndExplicitReplacementEndsComposition().

The focused selection is now10methods/15invocations. The full focus suite is
17methods/26invocations. The five changed Swift files pass frontend parsing;
UIKit execution remains for the owned Apple simulator. Shared PinkhaKit source
and tests are unchanged from the preserved9-method/11-invocation run, so that
pure-test evidence is reused without another execution.
