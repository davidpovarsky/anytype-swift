package annotationschema

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"reflect"
	"testing"

	"github.com/gogo/protobuf/proto"
	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/block/simple/dataview"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// These are the complete unmodified dataview Block bytes from stage
// 00-registered of actual original native run 45042110729, attempt 1, artifact
// 14762199006 (ZIP SHA256 270b824b9c0210cd1cd584db0315215678bfa04c29c4251692527c57e403fd6e).
// They are historical diagnostic inputs, not a live native state or authority.
const recordedLoadedBlock = "CghkYXRhdmlldxoAqgGtDhK2BwoHZGVmYXVsdBoDQWxsIigKEGxhc3RNb2RpZmllZERhdGUQATISYnlMYXN0TW9kaWZpZWREYXRlMgsKBG5hbWUQARjIATISCgtjcmVhdGVkRGF0ZRABGMgBMg4KB2NyZWF0b3IQARjIATIVChBsYXN0TW9kaWZpZWREYXRlGMgBMhMKDmxhc3RNb2RpZmllZEJ5GMgBMhMKDmxhc3RPcGVuZWREYXRlGMgBMhAKCWJhY2tsaW5rcxABGMgBMgkKA3RhZxABGGQyDAoFbGlua3MQARjIATIiCh1waW5raGFUb3JhaEFubm90YXRpb25Qcm90b2NvbBjIATIoCiNwaW5raGFUb3JhaEFubm90YXRpb25DbGFzc2lmaWNhdGlvbhjIATIjCh5waW5raGFUb3JhaEFubm90YXRpb25OYW1lc3BhY2UYyAEyHgoZcGlua2hhVG9yYWhBbm5vdGF0aW9uVVVJRBjIATItCihwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbkRlc3RpbmF0aW9uGMgBMikKJHBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uQWNjb3VudBjIATInCiJwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblNwYWNlGMgBMisKJnBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uTWVzc2FnZUlEGMgBMiwKJ3BpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uTXV0YXRpb25JRBjIATIqCiVwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblJldmlzaW9uGMgBMi4KKXBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uU291cmNlRGlnZXN0GMgBMi8KKnBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uUGF5bG9hZERpZ2VzdBjIATIqCiVwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkTWVzc2FnZUlEGMgBMisKJnBpbmtoYVRvcmFoQW5ub3RhdGlvbkFwcGxpZWRNdXRhdGlvbklEGMgBMikKJHBpbmtoYVRvcmFoQW5ub3RhdGlvbkFwcGxpZWRSZXZpc2lvbhjIATItCihwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkU291cmNlRGlnZXN0GMgBMi4KKXBpbmtoYVRvcmFoQW5ub3RhdGlvbkFwcGxpZWRQYXlsb2FkRGlnZXN0GMgBKggKBG5hbWUQASoPCgtjcmVhdGVkRGF0ZRAEKgsKB2NyZWF0b3IQZCoUChBsYXN0TW9kaWZpZWREYXRlEAQqEgoObGFzdE1vZGlmaWVkQnkQZCoSCg5sYXN0T3BlbmVkRGF0ZRAEKg0KCWJhY2tsaW5rcxBkKgcKA3RhZxALKgkKBWxpbmtzEGQqHwodcGlua2hhVG9yYWhBbm5vdGF0aW9uUHJvdG9jb2wqJQojcGlua2hhVG9yYWhBbm5vdGF0aW9uQ2xhc3NpZmljYXRpb24qIAoecGlua2hhVG9yYWhBbm5vdGF0aW9uTmFtZXNwYWNlKhsKGXBpbmtoYVRvcmFoQW5ub3RhdGlvblVVSUQqKgoocGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25EZXN0aW5hdGlvbiomCiRwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbkFjY291bnQqJAoicGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25TcGFjZSooCiZwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbk1lc3NhZ2VJRCopCidwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbk11dGF0aW9uSUQqJwolcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25SZXZpc2lvbiorCilwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblNvdXJjZURpZ2VzdCosCipwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblBheWxvYWREaWdlc3QqJwolcGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZE1lc3NhZ2VJRCooCiZwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkTXV0YXRpb25JRComCiRwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkUmV2aXNpb24qKgoocGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZFNvdXJjZURpZ2VzdCorCilwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkUGF5bG9hZERpZ2VzdDI7YmFmeXJlaWV4ZGYzNjVwZnF1bzNvdGJyNTJ6ajJicmhnaTNtZWR0cG5mN2h5aWplZ2ZmamxhNXV1eHE="
const recordedPersistedBlock = "CghkYXRhdmlld6oBrQ4StgcKB2RlZmF1bHQaA0FsbCIoChBsYXN0TW9kaWZpZWREYXRlEAEyEmJ5TGFzdE1vZGlmaWVkRGF0ZTILCgRuYW1lEAEYyAEyEgoLY3JlYXRlZERhdGUQARjIATIOCgdjcmVhdG9yEAEYyAEyFQoQbGFzdE1vZGlmaWVkRGF0ZRjIATITCg5sYXN0TW9kaWZpZWRCeRjIATITCg5sYXN0T3BlbmVkRGF0ZRjIATIQCgliYWNrbGlua3MQARjIATIJCgN0YWcQARhkMgwKBWxpbmtzEAEYyAEyIgodcGlua2hhVG9yYWhBbm5vdGF0aW9uUHJvdG9jb2wYyAEyKAojcGlua2hhVG9yYWhBbm5vdGF0aW9uQ2xhc3NpZmljYXRpb24YyAEyIwoecGlua2hhVG9yYWhBbm5vdGF0aW9uTmFtZXNwYWNlGMgBMh4KGXBpbmtoYVRvcmFoQW5ub3RhdGlvblVVSUQYyAEyLQoocGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25EZXN0aW5hdGlvbhjIATIpCiRwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbkFjY291bnQYyAEyJwoicGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25TcGFjZRjIATIrCiZwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbk1lc3NhZ2VJRBjIATIsCidwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvbk11dGF0aW9uSUQYyAEyKgolcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25SZXZpc2lvbhjIATIuCilwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblNvdXJjZURpZ2VzdBjIATIvCipwaW5raGFUb3JhaEFubm90YXRpb25DcmVhdGlvblBheWxvYWREaWdlc3QYyAEyKgolcGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZE1lc3NhZ2VJRBjIATIrCiZwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkTXV0YXRpb25JRBjIATIpCiRwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkUmV2aXNpb24YyAEyLQoocGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZFNvdXJjZURpZ2VzdBjIATIuCilwaW5raGFUb3JhaEFubm90YXRpb25BcHBsaWVkUGF5bG9hZERpZ2VzdBjIASoICgRuYW1lEAEqDwoLY3JlYXRlZERhdGUQBCoLCgdjcmVhdG9yEGQqFAoQbGFzdE1vZGlmaWVkRGF0ZRAEKhIKDmxhc3RNb2RpZmllZEJ5EGQqEgoObGFzdE9wZW5lZERhdGUQBCoNCgliYWNrbGlua3MQZCoHCgN0YWcQCyoJCgVsaW5rcxBkKh8KHXBpbmtoYVRvcmFoQW5ub3RhdGlvblByb3RvY29sKiUKI3BpbmtoYVRvcmFoQW5ub3RhdGlvbkNsYXNzaWZpY2F0aW9uKiAKHnBpbmtoYVRvcmFoQW5ub3RhdGlvbk5hbWVzcGFjZSobChlwaW5raGFUb3JhaEFubm90YXRpb25VVUlEKioKKHBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uRGVzdGluYXRpb24qJgokcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25BY2NvdW50KiQKInBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uU3BhY2UqKAomcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25NZXNzYWdlSUQqKQoncGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25NdXRhdGlvbklEKicKJXBpbmtoYVRvcmFoQW5ub3RhdGlvbkNyZWF0aW9uUmV2aXNpb24qKwopcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25Tb3VyY2VEaWdlc3QqLAoqcGlua2hhVG9yYWhBbm5vdGF0aW9uQ3JlYXRpb25QYXlsb2FkRGlnZXN0KicKJXBpbmtoYVRvcmFoQW5ub3RhdGlvbkFwcGxpZWRNZXNzYWdlSUQqKAomcGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZE11dGF0aW9uSUQqJgokcGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZFJldmlzaW9uKioKKHBpbmtoYVRvcmFoQW5ub3RhdGlvbkFwcGxpZWRTb3VyY2VEaWdlc3QqKwopcGlua2hhVG9yYWhBbm5vdGF0aW9uQXBwbGllZFBheWxvYWREaWdlc3QyO2JhZnlyZWlleGRmMzY1cGZxdW8zb3RicjUyemoyYnJoZ2kzbWVkdHBuZjdoeWlqZWdmZmpsYTV1dXhx"

func capturedNativeBlocks(t *testing.T) (*model.Block, *model.Block) {
	t.Helper()
	decode := func(encoded, expectedHash string) *model.Block {
		data, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil || fmt.Sprintf("%x", sha256.Sum256(data)) != expectedHash {
			t.Fatalf("retained actual native block differs: %v", err)
		}
		block := new(model.Block)
		if err := proto.Unmarshal(data, block); err != nil {
			t.Fatal(err)
		}
		if block.Id != "dataview" || block.GetDataview() == nil {
			t.Fatal("actual dataview block input is missing")
		}
		return block
	}
	live := decode(recordedLoadedBlock, "e3a887f3b59b008109579732906d1df35d6a5143457ca0b89e9238bd9b69eee9")
	persisted := decode(recordedPersistedBlock, "abf0bf27a11fe07f32ff022fadb4212a451a78902c3408c92ea5f08a4ceee002")
	if live.Restrictions == nil || persisted.Restrictions != nil ||
		!proto.Equal(live.Restrictions, &model.BlockRestrictions{}) || proto.Equal(live, persisted) {
		t.Fatal("retained native pair lost its actual nil-versus-empty difference")
	}
	return live, persisted
}

func TestOtzariaAnnotationSchemaNativeBlockSemantics(t *testing.T) {
	t.Run("OriginalDataviewDiffExplainsEmptyMessage", func(t *testing.T) {
		_, persisted := capturedNativeBlocks(t)
		before := proto.Clone(persisted).(*model.Block)
		left := dataview.NewDataview(proto.Clone(persisted).(*model.Block))
		right := dataview.NewDataview(proto.Clone(persisted).(*model.Block))
		messages, err := left.Diff("historical-comparison-control", right)
		if err != nil || len(messages) != 0 {
			t.Fatalf("original equal-block Diff emitted a persisted change: messages=%d err=%v", len(messages), err)
		}
		if left.Model().Restrictions == nil || right.Model().Restrictions == nil ||
			!proto.Equal(left.Model().Restrictions, &model.BlockRestrictions{}) ||
			!proto.Equal(right.Model().Restrictions, &model.BlockRestrictions{}) {
			t.Fatal("actual original Dataview/Base.Diff did not allocate the empty restrictions")
		}
		if !proto.Equal(before, persisted) || persisted.Restrictions != nil {
			t.Fatal("original diagnostic input was mutated")
		}
	})

	t.Run("CapturedNativePairUsesSemanticCopies", func(t *testing.T) {
		live, persisted := capturedNativeBlocks(t)
		liveBefore, persistedBefore := proto.Clone(live), proto.Clone(persisted)
		if !sameSchemaBlocksWithNativeDefaults([]*model.Block{live}, []*model.Block{persisted}) ||
			!sameSchemaBlocksWithNativeDefaults([]*model.Block{persisted}, []*model.Block{live}) {
			t.Fatal("actual native empty-presence pair was not semantically equal")
		}
		if !proto.Equal(liveBefore, live) || !proto.Equal(persistedBefore, persisted) || persisted.Restrictions != nil {
			t.Fatal("comparison changed an actual input")
		}
		copy := copySchemaBlockWithNativeDefaults(persisted)
		copy.Restrictions.Edit = true
		copy.GetDataview().Views[0].Name = "mutated comparison copy"
		copy.GetDataview().RelationLinks[0].Key = "mutated comparison copy"
		if !proto.Equal(liveBefore, live) || !proto.Equal(persistedBefore, persisted) {
			t.Fatal("comparison copy aliases original nested native state")
		}
		liveWire, err := proto.Marshal(live)
		if err != nil {
			t.Fatal(err)
		}
		persistedWire, err := proto.Marshal(persisted)
		if err != nil || bytes.Equal(liveWire, persistedWire) {
			t.Fatal("semantic comparison was incorrectly presented as wire equality")
		}
	})

	t.Run("NonzeroNativeRestrictionsRemainDifferent", func(t *testing.T) {
		_, persisted := capturedNativeBlocks(t)
		typeInfo := reflect.TypeOf(model.BlockRestrictions{})
		checked := 0
		for i := 0; i < typeInfo.NumField(); i++ {
			field := typeInfo.Field(i)
			if field.Type.Kind() != reflect.Bool || field.PkgPath != "" {
				t.Fatalf("original represented restriction shape changed; inspect field %s", field.Name)
			}
			changed := proto.Clone(persisted).(*model.Block)
			changed.Restrictions = &model.BlockRestrictions{}
			reflect.ValueOf(changed.Restrictions).Elem().Field(i).SetBool(true)
			if sameSchemaBlocksWithNativeDefaults([]*model.Block{changed}, []*model.Block{persisted}) ||
				sameSchemaBlocksWithNativeDefaults([]*model.Block{persisted}, []*model.Block{changed}) {
				t.Fatalf("nonzero native restriction %s was lost", field.Name)
			}
			if !sameSchemaBlocksWithNativeDefaults([]*model.Block{changed}, []*model.Block{proto.Clone(changed).(*model.Block)}) {
				t.Fatalf("identical nonzero native restriction %s was changed", field.Name)
			}
			checked++
		}
		if checked == 0 {
			t.Fatal("no original native restrictions were checked")
		}
	})

	t.Run("OtherNativeFieldsRemainDifferent", func(t *testing.T) {
		live, persisted := capturedNativeBlocks(t)
		changes := []struct {
			name   string
			change func(*model.Block)
		}{
			{"children", func(b *model.Block) { b.ChildrenIds = append(b.ChildrenIds, "unrelated-child") }},
			{"background", func(b *model.Block) { b.BackgroundColor = "unrelated-background" }},
			{"custom-field", func(b *model.Block) {
				b.Fields = &types.Struct{Fields: map[string]*types.Value{
					"unrecognized-application-key": {Kind: &types.Value_StringValue{StringValue: "must remain exact"}},
				}}
			}},
			{"view-name", func(b *model.Block) { b.GetDataview().Views[0].Name = "unrelated name" }},
			{"column-width", func(b *model.Block) { b.GetDataview().Views[0].Relations[0].Width++ }},
			{"column-visibility", func(b *model.Block) { b.GetDataview().Views[0].Relations[0].IsVisible = false }},
			{"relation-link", func(b *model.Block) { b.GetDataview().RelationLinks[0].Key = "unrelated-key" }},
			{"target-object", func(b *model.Block) { b.GetDataview().TargetObjectId = "unrelated-object" }},
		}
		for _, check := range changes {
			changed := proto.Clone(live).(*model.Block)
			check.change(changed)
			if sameSchemaBlocksWithNativeDefaults([]*model.Block{changed}, []*model.Block{persisted}) {
				t.Fatalf("unrelated represented native field was ignored: %s", check.name)
			}
		}
		if sameSchemaBlocksWithNativeDefaults([]*model.Block{live, live}, []*model.Block{persisted, persisted}) ||
			sameSchemaBlocksWithNativeDefaults([]*model.Block{live}, nil) ||
			sameSchemaBlocksWithNativeDefaults([]*model.Block{nil}, []*model.Block{persisted}) {
			t.Fatal("invalid block identity or membership was accepted")
		}
	})
}
