//go:build pinkha_loaded_account_witness

package localstorewitness

import (
	"context"
	"encoding/binary"
	"math"

	"github.com/anyproto/any-sync/app/ldiff"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/util/cidutil"
)

// This is the pinned native keyvalue.storageIdFromSpace contract. Only this
// exact system identity is classified separately from object trees. A caller
// cannot nominate an arbitrary missing tree root as a key-value store.
func nativeInventoryDefaultKeyValueID(spaceID string) (string, error) {
	raw, err := (&spacesyncproto.StorageHeader{
		SpaceId: spaceID, StorageName: "default",
	}).MarshalVT()
	if err != nil {
		return "", ErrNativeTreeInventory
	}
	id, err := cidutil.NewCidFromBytes(raw)
	if err != nil || id == "" {
		return "", ErrNativeTreeInventory
	}
	return id, nil
}

// nativeInventoryKeyValue binds the captured {id,h} system head to every row
// in its captured native collection, using the exact native ldiff algorithm.
// Full original signed/encrypted rows remain in Witness.WritePrivate. This
// structural identity check does not decrypt values or establish their ACL,
// signature/history semantics, remote freshness or migration completeness.
func (w *Witness) nativeInventoryKeyValue(ctx context.Context, id string, head row) (int, error) {
	fields, err := nativeInventoryFields(head, "id h")
	if err != nil {
		return 0, err
	}
	headID, err := nativeInventoryString(fields, "id", true)
	if err != nil || headID != id {
		return 0, ErrNativeTreeInventory
	}
	heads, err := nativeInventoryStrings(fields["h"], true)
	if err != nil || len(heads) != 1 {
		return 0, ErrNativeTreeInventory
	}
	collection := w.collection(id)
	if collection == nil {
		return 0, ErrNativeTreeInventory
	}
	elements := make([]ldiff.Element, 0, len(collection.rows))
	seen := map[string]bool{}
	for _, original := range collection.rows {
		if err := ctx.Err(); err != nil {
			return 0, err
		}
		values, err := nativeInventoryFields(original, "id k r v t i p dp")
		if err != nil {
			return 0, err
		}
		keyPeerID, err := nativeInventoryString(values, "id", true)
		if err != nil || seen[keyPeerID] || values["t"] == nil {
			return 0, ErrNativeTreeInventory
		}
		seen[keyPeerID] = true
		timestamp, err := values["t"].Float64()
		// Native anyenc timestamps are integral float64 microseconds. Values
		// outside the exact integer range cannot identify a stable native
		// LWW timestamp and must not be silently truncated or rounded.
		if err != nil || math.IsNaN(timestamp) || math.IsInf(timestamp, 0) ||
			math.Trunc(timestamp) != timestamp || math.Abs(timestamp) > 1<<53 {
			return 0, ErrNativeTreeInventory
		}
		var encoded [8]byte
		binary.BigEndian.PutUint64(encoded[:], uint64(int64(timestamp)))
		elements = append(elements, ldiff.Element{Id: keyPeerID, Head: string(encoded[:])})
	}
	diff := ldiff.New(32, 256)
	diff.Set(elements...)
	if diff.Hash() != heads[0] {
		return 0, ErrNativeTreeInventory
	}
	return len(elements), nil
}
