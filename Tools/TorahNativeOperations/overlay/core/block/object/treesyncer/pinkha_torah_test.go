package treesyncer

import (
	"context"
	"errors"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/commonspace/object/treemanager"
	"github.com/anyproto/any-sync/commonspace/settings"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahopscontract"
	"github.com/stretchr/testify/require"
)

type pinkhaReservedSettings struct {
	settings.SettingsObject
	id string
}

func (s *pinkhaReservedSettings) Id() string { return s.id }

type pinkhaSettingsManager struct {
	treemanager.TreeManager
	tree              objecttree.ObjectTree
	err               error
	calls             int
	spaceID, objectID string
}

func (m *pinkhaSettingsManager) GetTree(_ context.Context, spaceID, objectID string) (objecttree.ObjectTree, error) {
	m.calls++
	m.spaceID, m.objectID = spaceID, objectID
	return m.tree, m.err
}

func TestPinkhaSettingsLeaseUsesExistingReservedObject(t *testing.T) {
	reserved := &pinkhaReservedSettings{id: "settings"}
	manager := &pinkhaSettingsManager{tree: reserved}
	syncer := &treeSyncer{mainCtx: context.Background(), treeManager: manager, spaceId: "space", spaceSettingsId: "settings"}
	tree, err := syncer.PinkhaTorahSettingsTree(context.Background())
	require.NoError(t, err)
	require.Same(t, reserved, tree, "lease must share the actual deletion/sync object's mutex")
	require.Equal(t, 1, manager.calls)
	require.Equal(t, "space", manager.spaceID)
	require.Equal(t, "settings", manager.objectID)
	manager.tree = &pinkhaReservedSettings{id: "foreign"}
	_, err = syncer.PinkhaTorahSettingsTree(context.Background())
	require.ErrorIs(t, err, torahopscontract.ErrPrivateOperation)
	original := errors.New("closed native object manager")
	manager.err = original
	_, err = syncer.PinkhaTorahSettingsTree(context.Background())
	require.Same(t, original, err)
	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	before := manager.calls
	_, err = syncer.PinkhaTorahSettingsTree(cancelled)
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, before, manager.calls)
	syncer.mainCtx = cancelled
	_, err = syncer.PinkhaTorahSettingsTree(context.Background())
	require.ErrorIs(t, err, context.Canceled)
	require.Equal(t, before, manager.calls)
}
