package restriction

import (
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/stretchr/testify/require"
	"testing"
)

type privateHolder struct{}

func (privateHolder) Type() smartblock.SmartBlockType {
	return smartblock.SmartBlockTypePinkhaTorahOperations
}
func (privateHolder) Layout() (model.ObjectTypeLayout, bool) { return 0, false }
func (privateHolder) UniqueKey() domain.UniqueKey {
	return domain.MustUniqueKey(smartblock.SmartBlockTypePinkhaTorahOperations, "v1")
}
func (privateHolder) LocalDetails() *domain.Details { return domain.NewDetails() }
func (privateHolder) MemberPolicy() MemberPolicy    { return MemberPolicy{} }

func TestPinkhaPrivateHostDeniesGenericObjectMutations(t *testing.T) {
	holder := privateHolder{}
	restrictions := GetRestrictions(holder)
	byType := NewObjectRestrictionsFromValue(GetRestrictionsBySBType(holder.Type()))
	for _, mutation := range []model.RestrictionsObjectRestriction{
		model.Restrictions_Blocks, model.Restrictions_Relations, model.Restrictions_Details,
		model.Restrictions_Delete, model.Restrictions_LayoutChange, model.Restrictions_TypeChange,
		model.Restrictions_Template, model.Restrictions_Duplicate, model.Restrictions_Publish,
	} {
		require.ErrorIs(t, restrictions.Object.Check(mutation), ErrRestricted, mutation.String())
		require.ErrorIs(t, byType.Check(mutation), ErrRestricted, mutation.String())
	}
}
