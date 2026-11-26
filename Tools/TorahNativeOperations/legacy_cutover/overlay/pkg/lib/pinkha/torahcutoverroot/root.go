// Package torahcutoverroot owns only the separate native metadata root.
// Ordinary v1 associations keep their original root/type/validator unchanged.
package torahcutoverroot

import (
	"bytes"
	"errors"
	"strings"
	"unicode/utf8"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/tree/treechangeproto"
)

const (
	ChangeType       = "pinkha.torah.cutover.v1"
	Payload          = "store-change/legacy-cutover-v1"
	UniqueKeyPrefix  = "pinkhaTorahCutover"
	UniqueKeyVersion = "v1"
	// This is an explicit fork-local allocation, not an enabled numeric range.
	// In particular the existing rejected v1 neighbour 0x504B0002 stays invalid.
	SmartBlockType uint32 = 0x504B0101
)

var ErrPrivateRoot = errors.New("invalid private Torah cutover root")

func Root(spaceID string) (*treechangeproto.RawTreeChangeWithId, error) {
	if len(spaceID) == 0 || len(spaceID) > 1024 || !utf8.ValidString(spaceID) || strings.ContainsRune(spaceID, 0) {
		return nil, ErrPrivateRoot
	}
	return objecttree.DeriveObjectTreeRoot(objecttree.ObjectTreeDerivePayload{
		SpaceId: spaceID, ChangeType: ChangeType, ChangePayload: []byte(Payload), IsEncrypted: true,
	}, nil)
}

func ValidateRoot(spaceID string, raw *treechangeproto.RawTreeChangeWithId) error {
	expected, err := Root(spaceID)
	if err != nil || raw == nil || raw.Id != expected.Id || !bytes.Equal(raw.RawChange, expected.RawChange) {
		return errors.Join(ErrPrivateRoot, err)
	}
	return nil
}

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
	actual, err := root.MarshalVT()
	if err != nil {
		return err
	}
	canonical, err := decoded.MarshalVT()
	if err != nil {
		return err
	}
	if !bytes.Equal(actual, canonical) {
		return ErrPrivateRoot
	}
	return nil
}
