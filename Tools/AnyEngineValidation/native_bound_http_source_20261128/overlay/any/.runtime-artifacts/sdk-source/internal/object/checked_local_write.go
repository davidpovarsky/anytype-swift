package object

import (
	"context"
	"fmt"

	"github.com/anyproto/any-sync-sdk/internal/crdt"
)

// LocalReadCheck is an SDK-internal, read-only local storage predicate. It
// executes under the object's existing tree lock after catch-up and before
// mutation. It must not call network, user code, or any Object write method.
// No ACL lock is acquired or held by this hook.
type LocalReadCheck func(context.Context, *crdt.Controller) error

// LocalWriteWithLocalCheck preserves LocalWrite's DAG/validation/result path,
// adding one local predicate before append. It cannot upsert or address an
// implicit/multiple row. Used only by current-reader tech-space settings.
func (o *Object) LocalWriteWithLocalCheck(ctx context.Context, ch crdt.Change, check LocalReadCheck) (WriteResult, error) {
	if check == nil || len(ch.Records) != 1 || ch.Records[0].Id == "" || ch.Records[0].Upsert {
		return WriteResult{}, fmt.Errorf("%w: checked write requires one existing explicit row", crdt.ErrValidation)
	}
	return o.localWriteIf(ctx, ch, nil, nil, false, check)
}

// LocalSetWithLocalCheck preserves the device-local path and original result.
// Its predicate sees the row under the same lock as the subsequent LocalSet.
func (o *Object) LocalSetWithLocalCheck(ctx context.Context, ch crdt.Change, check LocalReadCheck) (WriteResult, error) {
	if check == nil || len(ch.Records) != 1 || ch.Records[0].Id == "" || ch.Records[0].Upsert {
		return WriteResult{}, fmt.Errorf("%w: checked local set requires one existing explicit row", crdt.ErrValidation)
	}
	return o.localSet(ctx, ch, check)
}
