package readguard

import "context"

// Value releases an owned, materialized member-only result only while the same
// signed ACL generation and captured account/Space lifetimes remain current.
// The read runs outside every authority lock. Its result stays private until
// the final short assignment; a failed read never releases a partial value.
// This helper is not for a live iterator, subscription, reader or callback.
func Value[T any](ctx context.Context, load LoadACL, read func() (T, error)) (out T, err error) {
	var admitted authority
	if err = withAuthority(ctx, load, nil, func(current authority) error {
		admitted = current
		return nil
	}); err != nil {
		return out, err
	}
	private, readErr := read()
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
