package readguard

import (
	"context"

	"github.com/anyproto/any-sync/commonspace/object/acl/list"
)

// Observation is a scalar snapshot taken under the original current-authority
// fence. It contains no mutable ACL object, lifetime token or key material.
type Observation struct {
	ACLID      string
	Identity   string
	HeadID     string
	ACLIsEmpty bool
}

// ObserveValue gives the materializer the exact signed generation it is bound
// to. Only scalar capture and final assignment run under authority locks; all
// caller work, including I/O and callbacks, runs outside those locks. No result
// is released if the account/Space retires, the head changes or read permission
// is lost. Existing Value and Reader behavior is unchanged.
func ObserveValue[T any](ctx context.Context, load LoadACL, read func(Observation) (T, error)) (out T, err error) {
	var admitted authority
	var observed Observation
	var loaded list.AclList
	loadObserved := func(ctx context.Context) (Scope, error) {
		scope, err := load(ctx)
		loaded = scope.ACL
		return scope, err
	}
	if err = withAuthority(ctx, loadObserved, nil, func(current authority) error {
		admitted = current
		observed = Observation{
			ACLID: current.aclID, Identity: current.identity, HeadID: current.headID,
			ACLIsEmpty: loaded.AclState().IsEmpty(),
		}
		return nil
	}); err != nil {
		return out, err
	}
	private, readErr := read(observed)
	err = withAuthority(ctx, load, &admitted, func(authority) error {
		if readErr == nil {
			out = private
		}
		return nil
	})
	if err != nil {
		return out, err
	}
	return out, readErr
}
