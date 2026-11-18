// Package torahopscontract owns the private, versioned native host identity.
// It has no application, projection, indexing or RPC dependencies.
package torahopscontract

import (
	"bytes"
	"errors"
	"strings"
	"unicode/utf8"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
)

const (
	ChangeType       = "pinkha.torah.operations.v1"
	Payload          = "store-change/immutable-claims-v1"
	UniqueKeyPrefix  = "pinkhaTorahOps"
	UniqueKeyVersion = "v1"
)

var ErrPrivateRoot = errors.New("invalid private Torah operations root")
var ErrPrivateOperation = errors.New("private Torah operations host does not support generic object operations")

// Root preserves the exact native identity exercised by the two-process proof.
// This is one root per Space, with no parent object, account-signature variant,
// random seed or dependency on T5's manifest.
func Root(spaceID string) (*treechangeproto.RawTreeChangeWithId, error) {
	if len(spaceID) == 0 || len(spaceID) > 1024 || !utf8.ValidString(spaceID) || strings.ContainsRune(spaceID, 0) {
		return nil, ErrPrivateRoot
	}
	return objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ChangeType: ChangeType, ChangePayload: []byte(Payload), IsEncrypted: true,
	}, nil)
}

// ValidateRoot requires the receiving Space as an independent input. Matching
// only an enum or a root's self-declared Space would permit a foreign binding.
func ValidateRoot(spaceID string, raw *treechangeproto.RawTreeChangeWithId) error {
	expected, err := Root(spaceID)
	if err != nil || raw == nil || raw.Id != expected.Id || !bytes.Equal(raw.RawChange, expected.RawChange) {
		return errors.Join(ErrPrivateRoot, err)
	}
	return nil
}

// ValidateRootChange checks every decoded root field against the canonical
// derived root. It does not replace ValidateRoot's CID/receiving-Space binding.
func ValidateRootChange(root *treechangeproto.RootChange) error {
	if root == nil || root.ChangeType != ChangeType {
		return ErrPrivateRoot
	}
	expected, err := Root(root.SpaceId)
	if err != nil {
		return err
	}
	decoded, err := objecttree.UnmarshallRoot(expected)
	if err != nil {
		return err
	}
	actualBytes, err := root.MarshalVT()
	if err != nil {
		return err
	}
	expectedBytes, err := decoded.MarshalVT()
	if err != nil {
		return err
	}
	if !bytes.Equal(actualBytes, expectedBytes) {
		return ErrPrivateRoot
	}
	return nil
}
