package objectcreator_test

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/gogo/protobuf/proto"

	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/object/objectcreator"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space/clientspace"
)

// This diagnostic owns no writer. It locks the already loaded original type,
// copies its NewState, and invokes the unchanged persisted-only observer. No
// Apply, repair, cache reload, normalization or comparison exclusion occurs.
func retainMissingAttachmentState(t *testing.T, f *nativeSchemaFixture, spc clientspace.Space, definition objectcreator.FixedSchemaDefinition, typeID, stage string) {
	t.Helper()
	record := map[string]any{
		"schema": "otzaria-missing-attachment-native-state-pair/1", "stage": stage,
		"process_id": os.Getpid(), "space_id": spc.Id(), "object_id": typeID,
		"expected_native_key": definition.Key.Marshal(), "diagnostic_only": true,
	}
	err := spc.DoCtx(f.ctx, typeID, func(object smartblock.SmartBlock) error {
		st := object.NewState()
		liveDetails, liveBlocks := st.Details().ToProto(), st.BlocksToSave()
		live, err := missingAttachmentStateCopy(liveDetails, liveBlocks)
		if err != nil {
			return err
		}
		live["heads"] = slices.Clone(object.Tree().Heads())
		record["live"] = live
		record["loaded_object_id"], record["loaded_space_id"] = object.Id(), object.SpaceID()
		if object.UniqueKey() != nil {
			record["loaded_native_key"] = object.UniqueKey().Marshal()
		}
		// The read-only helper retries only ErrFixedSchemaChanged for at most
		// five seconds; the live type remains locked for this paired capture.
		persisted, readErr := registrationDirectRead(f.ctx, f.observer, spc, definition)
		record["native_disposition"] = persisted.Disposition
		record["account_identity"] = persisted.AccountIdentity
		record["native_object_id"], record["native_space_id"] = persisted.ObjectID, persisted.SpaceID
		record["acl_id"], record["acl_head"] = persisted.ACLID, persisted.ACLHead
		record["archive_id"], record["archive_heads"] = persisted.ArchiveID, persisted.ArchiveHeads
		if readErr != nil {
			return readErr
		}
		persistedDetails, persistedBlocks := persisted.CopyPersistedSchemaState()
		copy, err := missingAttachmentStateCopy(persistedDetails, persistedBlocks)
		if err != nil {
			return err
		}
		copy["heads"] = slices.Clone(persisted.PersistedHeads)
		record["persisted"] = copy
		record["details_equal"] = proto.Equal(liveDetails, persistedDetails)
		record["blocks_equal"] = registrationBlocksEqual(liveBlocks, persistedBlocks)
		keys := make(map[string]bool)
		for key := range liveDetails.Fields {
			keys[key] = true
		}
		for key := range persistedDetails.Fields {
			keys[key] = true
		}
		var detailsDifferent []string
		for key := range keys {
			if !proto.Equal(liveDetails.Fields[key], persistedDetails.Fields[key]) {
				detailsDifferent = append(detailsDifferent, key)
			}
		}
		slices.Sort(detailsDifferent)
		record["different_detail_keys"] = detailsDifferent
		left, right := make(map[string]*model.Block), make(map[string]*model.Block)
		ids := make(map[string]bool)
		for _, block := range liveBlocks {
			if block != nil {
				left[block.Id], ids[block.Id] = block, true
			}
		}
		for _, block := range persistedBlocks {
			if block != nil {
				right[block.Id], ids[block.Id] = block, true
			}
		}
		var blocksDifferent []string
		for id := range ids {
			if !proto.Equal(left[id], right[id]) {
				blocksDifferent = append(blocksDifferent, id)
			}
		}
		slices.Sort(blocksDifferent)
		record["different_block_ids"] = blocksDifferent
		t.Logf("native paired state stage=%s details_equal=%t blocks_equal=%t detail_keys=%v block_ids=%v", stage,
			record["details_equal"], record["blocks_equal"], detailsDifferent, blocksDifferent)
		return nil
	})
	if err != nil {
		record["capture_error"] = err.Error()
		t.Errorf("native paired-state diagnostic stage=%s: %v", stage, err)
	}
	data, encodeErr := json.MarshalIndent(record, "", "  ")
	if encodeErr != nil {
		t.Errorf("encode paired-state diagnostic: %v", encodeErr)
		return
	}
	directory := os.Getenv("OTZARIA_ANNOTATION_SCHEMA_EVIDENCE")
	if directory == "" {
		t.Error("paired-state diagnostic has no owned evidence directory")
		return
	}
	file, openErr := os.OpenFile(filepath.Join(directory, "missing-attachment-"+stage+".json"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if openErr != nil {
		t.Errorf("retain paired-state diagnostic: %v", openErr)
		return
	}
	_, writeErr := file.Write(append(data, '\n'))
	if err := errors.Join(writeErr, file.Sync(), file.Close()); err != nil {
		t.Errorf("persist paired-state diagnostic: %v", err)
	}
}

func missingAttachmentStateCopy(details proto.Message, blocks []*model.Block) (map[string]any, error) {
	detailsBytes, err := proto.Marshal(details)
	if err != nil {
		return nil, err
	}
	detailsJSON, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}
	var copiedBlocks []map[string]any
	for _, block := range blocks {
		data, err := proto.Marshal(block)
		if err != nil {
			return nil, err
		}
		blockJSON, err := json.Marshal(block)
		if err != nil {
			return nil, err
		}
		copiedBlocks = append(copiedBlocks, map[string]any{
			"id": block.Id, "protobuf": data, "sha256": missingAttachmentHash(data),
			"json": json.RawMessage(blockJSON),
		})
	}
	return map[string]any{"details_protobuf": detailsBytes, "details_sha256": missingAttachmentHash(detailsBytes),
		"details_json": json.RawMessage(detailsJSON), "blocks": copiedBlocks}, nil
}

func missingAttachmentHash(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}
