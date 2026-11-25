//go:build pinkha_loaded_account_witness

package export

import (
	"fmt"
	"sort"

	"github.com/gogo/protobuf/proto"
	"github.com/ipfs/go-cid"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// NativeFileReference records the exact raw snapshot owner and field. Legacy
// direct file IDs remain distinguishable from native file-object references.
type NativeFileReference struct {
	OwnerObjectID  string
	Field          string
	TargetObjectID string
	FileID         string
	LegacyFileID   bool
}

func (w *NativeRawObject) FileInfo() (*model.FileInfo, error) {
	row, err := w.capturedRow()
	if err != nil {
		return nil, err
	}
	if row.Snapshot.FileInfo == nil {
		return nil, nil
	}
	return proto.Clone(row.Snapshot.FileInfo).(*model.FileInfo), nil
}

// FileReferences enumerates every file location supported by the native
// current-state schema. It deliberately does not invoke State.FileRelationKeys,
// whose error behavior skips unknown property formats. Missing formats and
// unresolved object/file IDs become explicit closed-resolver entries.
func (r *NativeCapturedResolver) FileReferences() ([]NativeFileReference, error) {
	if r == nil || r.resolver == nil {
		return nil, ErrNativeObjectWitness
	}
	ids := make([]string, 0, len(r.objects))
	fileOwners := map[string][]string{}
	for id, object := range r.objects {
		ids = append(ids, id)
		info, err := object.FileInfo()
		if err != nil {
			return nil, err
		}
		if info != nil && info.FileId != "" {
			fileOwners[info.FileId] = append(fileOwners[info.FileId], id)
		}
	}
	sort.Strings(ids)
	var refs []NativeFileReference
	for _, id := range ids {
		row, err := r.objects[id].capturedRow()
		if err != nil {
			return nil, err
		}
		add := func(field, target string, legacy bool) {
			if target == "" {
				return
			}
			ref := NativeFileReference{OwnerObjectID: id, Field: field, LegacyFileID: legacy}
			if legacy {
				ref.FileID = target
				if len(fileOwners[target]) == 0 {
					r.resolver.RecordUnmapped(id, field, target, "legacy-file-without-captured-native-file-info")
				}
			} else {
				ref.TargetObjectID = target
				targetObject := r.objects[target]
				if targetObject != nil {
					info, infoErr := targetObject.FileInfo()
					if infoErr == nil && info != nil {
						ref.FileID = info.FileId
					}
				}
				if ref.FileID == "" {
					// Historical bookmark/icon fields may still contain direct native CIDs.
					if len(fileOwners[target]) > 0 {
						ref.FileID, ref.LegacyFileID = target, true
					} else {
						r.resolver.RecordUnmapped(id, field, target, "file-reference-without-captured-native-file-info")
					}
				}
			}
			refs = append(refs, ref)
		}
		if info := row.Snapshot.FileInfo; info != nil {
			if info.FileId == "" {
				r.resolver.RecordUnmapped(id, "fileInfo.fileId", "", "empty-native-file-id")
			} else {
				refs = append(refs, NativeFileReference{OwnerObjectID: id, Field: "fileInfo.fileId", TargetObjectID: id, FileID: info.FileId})
			}
		}
		// Legacy snapshot FileKeys are not discarded even when current FileInfo
		// admission is unavailable. Native history keys remain in the raw witness.
		if row.Snapshot.FileKeys != nil && len(row.Snapshot.FileKeys.Fields) > 0 {
			r.resolver.RecordUnmapped(id, "fileKeys", "", "legacy-snapshot-file-keys-require-native-history-admission")
		}
		for index, block := range row.Snapshot.Blocks {
			if block == nil {
				r.resolver.RecordUnmapped(id, fmt.Sprintf("blocks[%d]", index), "", "nil-native-block")
				continue
			}
			prefix := fmt.Sprintf("blocks[%d](%s)", index, block.Id)
			if file := block.GetFile(); file != nil {
				add(prefix+".file.targetObjectId", file.TargetObjectId, false)
				// Keep an obsolete direct hash explicitly; it may name a distinct retained
				// payload. A target object's presence must not erase the older native ID.
				if file.Hash != "" {
					add(prefix+".file.hash", file.Hash, true)
				}
			}
			if mark := block.GetBookmark(); mark != nil {
				add(prefix+".bookmark.imageHash", mark.ImageHash, false)
				add(prefix+".bookmark.faviconHash", mark.FaviconHash, false)
			}
			if text := block.GetText(); text != nil {
				add(prefix+".text.iconImage", text.IconImage, false)
			}
		}
		opts, err := r.resolver.OptionsForObject(id)
		if err != nil {
			return nil, err
		}
		details := domain.NewDetailsFromProto(row.Snapshot.Details)
		for key := range details.IterateKeys() {
			if key == bundle.RelationKeyCoverId {
				kind := details.GetInt64(bundle.RelationKeyCoverType)
				if kind == 1 || kind == 4 || kind == 5 {
					value := details.GetString(key)
					if _, err := cid.Decode(value); err == nil {
						add("details."+string(key), value, false)
					}
				}
				continue
			}
			format, ok := opts.ResolveFormat(key)
			if !ok {
				continue
			} // The closed resolver records this exact missing key.
			if format != model.RelationFormat_file {
				continue
			}
			value := details.Get(key)
			if _, ok := value.TryString(); !ok {
				if _, ok := value.TryStringList(); !ok {
					r.resolver.RecordUnmapped(id, "details."+string(key), "", "unsupported-file-reference-value")
					continue
				}
			}
			for index, target := range details.WrapToStringList(key) {
				add(fmt.Sprintf("details.%s[%d]", key, index), target, false)
			}
		}
	}
	sort.Slice(refs, func(i, j int) bool {
		if refs[i].OwnerObjectID != refs[j].OwnerObjectID {
			return refs[i].OwnerObjectID < refs[j].OwnerObjectID
		}
		if refs[i].Field != refs[j].Field {
			return refs[i].Field < refs[j].Field
		}
		return refs[i].FileID < refs[j].FileID
	})
	return refs, nil
}
