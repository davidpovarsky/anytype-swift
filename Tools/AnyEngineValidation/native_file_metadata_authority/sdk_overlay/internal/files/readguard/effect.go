package readguard

import "context"

// Effect admits one cache operation against the captured account/Space and
// current signed read authority. prepare may read immutable row/service inputs
// but must not change storage, queue work or call user code. Its returned action
// contains every effect and runs only after the same authority is rechecked.
//
// The final short authority check is the admission point. All ACL/lifetime locks
// are released before action runs. A later removal or retirement does not undo
// an already admitted effect or replace its original result with an authority
// error. The caller passes its original context to the underlying operation;
// this helper neither retries it nor promises cancellation of earlier jobs.
func Effect(ctx context.Context, load LoadACL, prepare func() (func() error, error)) error {
	var admitted authority
	if err := withAuthority(ctx, load, nil, func(current authority) error {
		admitted = current
		return nil
	}); err != nil {
		return err
	}
	action, prepareErr := prepare()
	if err := withAuthority(ctx, load, &admitted, nil); err != nil {
		return err
	}
	if prepareErr != nil {
		return prepareErr
	}
	if action == nil {
		return nil // An inline/no-work result still required current admission.
	}
	return action()
}
