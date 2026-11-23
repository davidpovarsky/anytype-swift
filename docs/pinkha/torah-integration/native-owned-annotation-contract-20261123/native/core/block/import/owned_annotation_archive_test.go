package importer

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/gogo/protobuf/types"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Base ZIPs must be produced by the genuine original native application export
// fixture in this run. Derived mutations are rejection probes, not native
// export specimens. There is no synthetic fallback.
func TestOtzariaOwnedAnnotationArchive(t *testing.T) {
	fixtures := make(map[string]ownedArchiveTestFixture)
	for _, label := range []string{"text", "format", "nested", "attachment"} {
		f := readOwnedArchiveTestFixture(t, label)
		fixtures[label] = f
		if !t.Run("Original_"+label, func(t *testing.T) {
			a, err := inspectOwnedAnnotationArchive(context.Background(), f.raw, sha256.Sum256(f.raw), f.root, f.space)
			ownedArchiveTestNoError(t, err)
			if len(a.inventory()) != f.members || a.snapshots[f.root] == nil {
				t.Fatal("actual original member/root inventory changed")
			}
		}) {
			return
		}
	}
	base := fixtures["text"]
	attachment := fixtures["attachment"]
	record := []map[string]any{}
	refused := func(name, code string, f ownedArchiveTestFixture, variant []byte) {
		t.Run(name, func(t *testing.T) {
			_, err := inspectOwnedAnnotationArchive(context.Background(), variant, sha256.Sum256(variant), f.root, f.space)
			if err == nil || !strings.Contains(err.Error(), code) {
				t.Fatalf("expected fixed refusal %s, got %v", code, err)
			}
			h := sha256.Sum256(variant)
			record = append(record, map[string]any{"case": name, "base_specimen": f.name, "base_sha256": f.hash,
				"variant_sha256": hex.EncodeToString(h[:]), "refusal": code})
		})
	}
	t.Run("ImmutableExclusiveOwnedStaging", func(t *testing.T) {
		callerBytes := bytes.Clone(base.raw)
		a, err := inspectOwnedAnnotationArchive(context.Background(), callerBytes, sha256.Sum256(callerBytes), base.root, base.space)
		ownedArchiveTestNoError(t, err)
		callerBytes[0] ^= 0xff
		inventory := a.inventory()
		inventory[0].Name = "caller change"
		if a.inventory()[0].Name == "caller change" {
			t.Fatal("inventory aliases mutable caller storage")
		}
		first, err := a.stage(context.Background())
		ownedArchiveTestNoError(t, err)
		defer first.Close()
		second, err := a.stage(context.Background())
		ownedArchiveTestNoError(t, err)
		defer second.Close()
		if first.root == second.root || first.archivePath == second.archivePath || first.TempDir() == second.TempDir() || first.TempDir() == first.root {
			t.Fatal("staging did not create independent owner directories")
		}
		for _, stage := range []*ownedAnnotationArchiveStaging{first, second} {
			for _, directory := range []string{stage.root, stage.TempDir()} {
				info, err := os.Lstat(directory)
				ownedArchiveTestNoError(t, err)
				if !info.IsDir() || info.Mode().Perm() != 0700 {
					t.Fatal("owned staging directory mode is not 0700")
				}
			}
			info, err := os.Lstat(stage.archivePath)
			ownedArchiveTestNoError(t, err)
			if !info.Mode().IsRegular() || info.Mode().Perm() != 0600 {
				t.Fatal("owned archive mode is not 0600")
			}
			raw, err := os.ReadFile(stage.archivePath)
			ownedArchiveTestNoError(t, err)
			if !bytes.Equal(raw, base.raw) || sha256.Sum256(raw) != stage.digest {
				t.Fatal("staged bytes differ from owned admitted input")
			}
		}
		ownedArchiveTestNoError(t, first.Close())
		if _, err := os.Stat(first.root); !errors.Is(err, os.ErrNotExist) {
			t.Fatal("first owned staging root was not removed")
		}
		if _, err := os.Stat(second.archivePath); err != nil {
			t.Fatal("closing one owner changed another owner's archive")
		}
		ownedArchiveTestNoError(t, first.Close())
		ownedArchiveTestNoError(t, second.Close())
		if _, err := os.Stat(second.root); !errors.Is(err, os.ErrNotExist) {
			t.Fatal("second owned staging root was not removed")
		}
	})
	t.Run("CancellationAndIdentityComparisons", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		if _, err := inspectOwnedAnnotationArchive(ctx, base.raw, sha256.Sum256(base.raw), base.root, base.space); !errors.Is(err, context.Canceled) {
			t.Fatal("canceled admission did not preserve actual cancellation")
		}
		a, err := inspectOwnedAnnotationArchive(context.Background(), base.raw, sha256.Sum256(base.raw), base.root, base.space)
		ownedArchiveTestNoError(t, err)
		if _, err := a.stage(ctx); !errors.Is(err, context.Canceled) {
			t.Fatal("canceled preparation produced an accepted stage")
		}
		for _, input := range []struct {
			digest            [32]byte
			root, space, code string
		}{
			{[32]byte{}, base.root, base.space, "digest_mismatch"},
			{sha256.Sum256(base.raw), "unowned-root", base.space, "missing_root"},
			{sha256.Sum256(base.raw), base.root, "different-space", "snapshot_identity"},
		} {
			_, err := inspectOwnedAnnotationArchive(context.Background(), base.raw, input.digest, input.root, input.space)
			if err == nil || !strings.Contains(err.Error(), input.code) {
				t.Fatalf("exact data comparison missing: %s: %v", input.code, err)
			}
		}
	})
	refused("CompressedBudget", "compressed_budget", base, append(bytes.Clone(base.raw), make([]byte, ownedArchiveMaxBytes)...))
	refused("HiddenPrefix", "zip_framing", base, append([]byte("hidden"), base.raw...))
	refused("TrailingBytes", "zip_framing", base, append(bytes.Clone(base.raw), []byte("trailing")...))
	rootMember, rootBody := ownedArchiveRootMember(t, base)
	for _, path := range []struct{ name, value string }{
		{"TraversalPath", "../outside.pb"}, {"AbsolutePath", "/outside.pb"}, {"BackslashPath", "objects\\outside.pb"},
	} {
		variant := ownedArchiveRewrite(t, base.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
			if h.Name == rootMember {
				h.Name = path.value
			}
			return body, true
		}, nil)
		refused(path.name, "zip_framing", base, variant)
	}
	variant := ownedArchiveRewrite(t, base.raw, nil, func(w *zip.Writer) {
		ownedArchiveAdd(t, w, zip.FileHeader{Name: strings.ToUpper(rootMember), Method: zip.Deflate}, rootBody)
	})
	refused("CaseAliasedDuplicate", "zip_duplicate_path", base, variant)
	variant = ownedArchiveRewrite(t, base.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
		if h.Name == rootMember {
			h.SetMode(os.ModeSymlink | 0777)
		}
		return body, true
	}, nil)
	refused("SymlinkMember", "zip_member_mismatch", base, variant)
	variant = ownedArchiveRewrite(t, base.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
		if h.Name == rootMember {
			return bytes.Repeat([]byte("a"), ownedArchiveMaxExpanded+1), true
		}
		return body, true
	}, nil)
	refused("ExpandedBudget", "expanded_budget", base, variant)
	variant = ownedArchiveRewrite(t, base.raw, nil, func(w *zip.Writer) {
		ownedArchiveAdd(t, w, zip.FileHeader{Name: "profile", Method: zip.Deflate}, []byte("unexpected account metadata"))
	})
	refused("UnexpectedMetadata", "unsupported_member", base, variant)
	variant = ownedArchiveRewrite(t, attachment.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
		return body, h.Name != attachment.fileSource
	}, nil)
	refused("MissingBinary", "file_inventory", attachment, variant)
	variant = ownedArchiveRewrite(t, base.raw, nil, func(w *zip.Writer) {
		ownedArchiveAdd(t, w, zip.FileHeader{Name: "files/unclaimed.bin", Method: zip.Deflate}, []byte("unreferenced binary"))
	})
	refused("UnclaimedBinary", "file_inventory", base, variant)
	for _, source := range []struct{ name, value string }{
		{"FileSourceOutside", "../../not-owned"}, {"FileSourceURL", "https://invalid.example/foreign"}, {"FileSourceNested", "files/nested/file"},
	} {
		variant = ownedArchiveRewrite(t, attachment.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
			if !strings.HasSuffix(h.Name, ".pb") {
				return body, true
			}
			snapshot := &pb.SnapshotWithType{}
			ownedArchiveTestNoError(t, snapshot.Unmarshal(body))
			if coresb.SmartBlockType(snapshot.SbType) != coresb.SmartBlockTypeFileObject {
				return body, true
			}
			details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
			if details.GetString(bundle.RelationKeySource) != attachment.fileSource {
				return body, true
			}
			details.SetString(bundle.RelationKeySource, source.value)
			snapshot.Snapshot.Data.Details = details.ToProto()
			encoded, err := snapshot.Marshal()
			ownedArchiveTestNoError(t, err)
			return encoded, true
		}, nil)
		refused(source.name, "file_source", attachment, variant)
	}
	variant = ownedArchiveRewrite(t, attachment.raw, func(h *zip.FileHeader, body []byte) ([]byte, bool) {
		if !strings.HasSuffix(h.Name, ".pb") {
			return body, true
		}
		snapshot := &pb.SnapshotWithType{}
		ownedArchiveTestNoError(t, snapshot.Unmarshal(body))
		if coresb.SmartBlockType(snapshot.SbType) == coresb.SmartBlockTypeFileObject {
			snapshot.Snapshot.Data.FileInfo = nil
			encoded, err := snapshot.Marshal()
			ownedArchiveTestNoError(t, err)
			return encoded, true
		}
		return body, true
	}, nil)
	refused("MissingOriginalFileInfo", "file_source", attachment, variant)
	replaceRoot := func(body []byte) []byte {
		return ownedArchiveRewrite(t, base.raw, func(h *zip.FileHeader, original []byte) ([]byte, bool) {
			if h.Name == rootMember {
				return body, true
			}
			return original, true
		}, nil)
	}
	refused("DuplicateSingular", "wire_duplicate_singular", base, replaceRoot(
		append(bytes.Clone(rootBody), ownedArchiveRawField(t, rootBody, 2)...)))
	duplicateMap := ownedArchiveReplaceWire(t, rootBody, []uint64{2, 2, 2}, func(details []byte) []byte {
		return append(bytes.Clone(details), ownedArchiveRawField(t, details, 1)...)
	})
	refused("DuplicateMapKey", "wire_duplicate_map_key", base, replaceRoot(duplicateMap))
	snapshot := &pb.SnapshotWithType{}
	ownedArchiveTestNoError(t, snapshot.Unmarshal(rootBody))
	details := domain.NewDetailsFromProto(snapshot.Snapshot.Data.Details)
	details.SetString(domain.RelationKey("\u00c5"), "first")
	details.SetString(domain.RelationKey("A\u030a"), "second")
	snapshot.Snapshot.Data.Details = details.ToProto()
	collision, err := snapshot.Marshal()
	ownedArchiveTestNoError(t, err)
	refused("CanonicalMapCollision", "wire_duplicate_map_key", base, replaceRoot(collision))
	other := &model.Block{Content: &model.BlockContentOfLink{Link: &model.BlockContentLink{TargetBlockId: base.root}}}
	otherContent, err := other.Marshal()
	ownedArchiveTestNoError(t, err)
	oneof := ownedArchiveReplaceWire(t, rootBody, []uint64{2, 2, 1}, func(block []byte) []byte {
		return append(bytes.Clone(block), otherContent...)
	})
	refused("DuplicateOneof", "wire_duplicate_oneof", base, replaceRoot(oneof))
	unknown := binary.AppendUvarint(bytes.Clone(rootBody), 19000<<3)
	unknown = binary.AppendUvarint(unknown, 1)
	refused("UnknownSnapshotField", "wire_unknown_field", base, replaceRoot(unknown))
	// Unmarshal into a fresh original model; merge semantics must not carry
	// the preceding deliberately ambiguous map into this distinct probe.
	snapshot = &pb.SnapshotWithType{}
	ownedArchiveTestNoError(t, snapshot.Unmarshal(rootBody))
	nested := &types.Value{Kind: &types.Value_StringValue{StringValue: "bounded nested test"}}
	for range 40 {
		nested = &types.Value{Kind: &types.Value_StructValue{StructValue: &types.Struct{Fields: map[string]*types.Value{"nested": nested}}}}
	}
	snapshot.Snapshot.Data.Details.Fields["wireDepthProbe"] = nested
	deep, err := snapshot.Marshal()
	ownedArchiveTestNoError(t, err)
	refused("WireDepthBudget", "wire_message_or_depth", base, replaceRoot(deep))
	refused("CRCFailure", "zip_member_crc_or_size", base, ownedArchiveCorruptCRC(t, base.raw))
	refused("EncryptedFlags", "zip_framing", base, ownedArchiveChangeFlags(t, base.raw, 1))
	zr, err := zip.NewReader(bytes.NewReader(base.raw), int64(len(base.raw)))
	ownedArchiveTestNoError(t, err)
	offset, err := zr.File[0].DataOffset()
	ownedArchiveTestNoError(t, err)
	central := int(binary.LittleEndian.Uint32(base.raw[len(base.raw)-6:]))
	local := int(binary.LittleEndian.Uint32(base.raw[central+42:]))
	mismatch := bytes.Clone(base.raw)
	mismatch[local+30] ^= 1
	refused("LocalCentralNameMismatch", "zip_framing", base, mismatch)
	descriptorMismatch := bytes.Clone(base.raw)
	dd := int(offset) + int(zr.File[0].CompressedSize64)
	if zr.File[0].Flags&8 == 0 {
		t.Fatal("authentic original writer did not emit its expected data descriptor")
	}
	if binary.LittleEndian.Uint32(descriptorMismatch[dd:]) == 0x08074b50 {
		dd += 4
	}
	descriptorMismatch[dd] ^= 1
	refused("DescriptorMismatch", "zip_framing", base, descriptorMismatch)
	encoded, err := json.MarshalIndent(map[string]any{
		"schema": 1, "genuine_base_specimens": 4, "derived_rejection_cases": record,
		"archive_admission_only": true, "native_import_activated": false, "body_ack_authority": false,
	}, "", "  ")
	ownedArchiveTestNoError(t, err)
	ownedArchiveTestNoError(t, os.WriteFile(filepath.Join(os.Getenv("OTZARIA_NATIVE_EXPORT_FIXTURES"),
		"archive-admission-rejections.json"), append(encoded, '\n'), 0600))
}

type ownedArchiveTestFixture struct {
	name       string
	raw        []byte
	hash       string
	root       string
	space      string
	members    int
	fileSource string
}

func readOwnedArchiveTestFixture(t *testing.T, label string) ownedArchiveTestFixture {
	t.Helper()
	directory := os.Getenv("OTZARIA_NATIVE_EXPORT_FIXTURES")
	if directory == "" || !filepath.IsAbs(directory) {
		t.Fatal("genuine native export directory required; no synthetic fallback")
	}
	encoded, err := os.ReadFile(filepath.Join(directory, label+"-manifest.json"))
	ownedArchiveTestNoError(t, err)
	var manifest struct {
		Schema          int
		Specimen        string
		Archive         string
		Hash            string `json:"archive_sha256"`
		Bytes           int    `json:"archive_bytes"`
		Root            string `json:"root_id"`
		Space           string `json:"space_id"`
		Members         []json.RawMessage
		FileSource      string `json:"attachment_source"`
		ExportSuccess   bool   `json:"original_export_report_success"`
		ImportActivated bool   `json:"native_import_activated"`
	}
	ownedArchiveTestNoError(t, json.Unmarshal(encoded, &manifest))
	if manifest.Schema != 1 || manifest.Specimen != label || manifest.Archive != label+".zip" || !manifest.ExportSuccess ||
		manifest.ImportActivated || manifest.Root == "" || manifest.Space == "" {
		t.Fatal("actual native producer evidence is incomplete")
	}
	raw, err := os.ReadFile(filepath.Join(directory, label+".zip"))
	ownedArchiveTestNoError(t, err)
	hash := sha256.Sum256(raw)
	if len(raw) != manifest.Bytes || hex.EncodeToString(hash[:]) != manifest.Hash {
		t.Fatal("actual native specimen bytes changed")
	}
	return ownedArchiveTestFixture{name: label, raw: raw, hash: manifest.Hash, root: manifest.Root, space: manifest.Space,
		members: len(manifest.Members), fileSource: manifest.FileSource}
}
func ownedArchiveRootMember(t *testing.T, f ownedArchiveTestFixture) (string, []byte) {
	t.Helper()
	zr, err := zip.NewReader(bytes.NewReader(f.raw), int64(len(f.raw)))
	ownedArchiveTestNoError(t, err)
	for _, member := range zr.File {
		if strings.HasSuffix(member.Name, "/"+f.root+".pb") {
			r, err := member.Open()
			ownedArchiveTestNoError(t, err)
			raw, err := io.ReadAll(r)
			ownedArchiveTestNoError(t, err)
			ownedArchiveTestNoError(t, r.Close())
			return member.Name, raw
		}
	}
	t.Fatal("genuine root snapshot member absent")
	return "", nil
}
func ownedArchiveRewrite(t *testing.T, raw []byte, change func(*zip.FileHeader, []byte) ([]byte, bool), extra func(*zip.Writer)) []byte {
	t.Helper()
	zr, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	ownedArchiveTestNoError(t, err)
	var buffer bytes.Buffer
	w := zip.NewWriter(&buffer)
	for _, member := range zr.File {
		r, err := member.Open()
		ownedArchiveTestNoError(t, err)
		body, err := io.ReadAll(r)
		ownedArchiveTestNoError(t, err)
		ownedArchiveTestNoError(t, r.Close())
		header := member.FileHeader
		header.Extra = bytes.Clone(member.Extra)
		// Keep authentic DOS time and timestamp extra without appending a
		// second extra while writing a derived controlled rejection variant.
		header.Modified = time.Time{}
		keep := true
		if change != nil {
			body, keep = change(&header, body)
		}
		if keep {
			ownedArchiveAdd(t, w, header, body)
		}
	}
	if extra != nil {
		extra(w)
	}
	ownedArchiveTestNoError(t, w.Close())
	return buffer.Bytes()
}
func ownedArchiveAdd(t *testing.T, w *zip.Writer, header zip.FileHeader, body []byte) {
	t.Helper()
	stream, err := w.CreateHeader(&header)
	ownedArchiveTestNoError(t, err)
	_, err = stream.Write(body)
	ownedArchiveTestNoError(t, err)
}

// Independent minimal navigation only constructs probes over trusted actual
// exporter bytes. This is not the wire admission scanner under test.
func ownedArchiveFieldSpan(t *testing.T, raw []byte) (number, wire uint64, tagBytes, start, end int) {
	t.Helper()
	tag, n := binary.Uvarint(raw)
	if n <= 0 {
		t.Fatal("invalid genuine wire tag")
	}
	number, wire, tagBytes = tag>>3, tag&7, n
	start = n
	switch wire {
	case 0:
		_, size := binary.Uvarint(raw[n:])
		if size <= 0 {
			t.Fatal("invalid genuine varint")
		}
		end = n + size
	case 1:
		end = n + 8
	case 2:
		length, size := binary.Uvarint(raw[n:])
		if size <= 0 {
			t.Fatal("invalid genuine length")
		}
		start = n + size
		end = start + int(length)
	case 5:
		end = n + 4
	default:
		t.Fatal("unsupported genuine wire type")
	}
	if end > len(raw) {
		t.Fatal("invalid genuine wire range")
	}
	return
}
func ownedArchiveRawField(t *testing.T, raw []byte, requested uint64) []byte {
	t.Helper()
	for len(raw) > 0 {
		number, _, _, _, end := ownedArchiveFieldSpan(t, raw)
		if number == requested {
			return bytes.Clone(raw[:end])
		}
		raw = raw[end:]
	}
	t.Fatal("required actual generated field absent")
	return nil
}
func ownedArchiveReplaceWire(t *testing.T, raw []byte, path []uint64, mutate func([]byte) []byte) []byte {
	t.Helper()
	if len(path) == 0 {
		return mutate(raw)
	}
	result := []byte{}
	for len(raw) > 0 {
		number, wire, tagBytes, start, end := ownedArchiveFieldSpan(t, raw)
		if number == path[0] {
			if wire != 2 {
				t.Fatal("actual mutation path is not a generated submessage")
			}
			child := ownedArchiveReplaceWire(t, raw[start:end], path[1:], mutate)
			result = append(result, raw[:tagBytes]...)
			result = binary.AppendUvarint(result, uint64(len(child)))
			result = append(result, child...)
			result = append(result, raw[end:]...)
			return result
		}
		result = append(result, raw[:end]...)
		raw = raw[end:]
	}
	t.Fatal("required actual generated mutation path absent")
	return nil
}
func ownedArchiveCorruptCRC(t *testing.T, raw []byte) []byte {
	t.Helper()
	zr, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	ownedArchiveTestNoError(t, err)
	file := zr.File[0]
	offset, err := file.DataOffset()
	ownedArchiveTestNoError(t, err)
	result := bytes.Clone(raw)
	cd := int(binary.LittleEndian.Uint32(raw[len(raw)-6:]))
	newCRC := file.CRC32 ^ 1
	binary.LittleEndian.PutUint32(result[cd+16:], newCRC)
	local := int(binary.LittleEndian.Uint32(raw[cd+42:]))
	if file.Flags&8 != 0 {
		dd := int(offset) + int(file.CompressedSize64)
		if binary.LittleEndian.Uint32(result[dd:]) == 0x08074b50 {
			dd += 4
		}
		binary.LittleEndian.PutUint32(result[dd:], newCRC)
		if binary.LittleEndian.Uint32(result[local+14:]) != 0 {
			binary.LittleEndian.PutUint32(result[local+14:], newCRC)
		}
	} else {
		binary.LittleEndian.PutUint32(result[local+14:], newCRC)
	}
	return result
}
func ownedArchiveChangeFlags(t *testing.T, raw []byte, bit uint16) []byte {
	t.Helper()
	result := bytes.Clone(raw)
	cd := int(binary.LittleEndian.Uint32(raw[len(raw)-6:]))
	local := int(binary.LittleEndian.Uint32(raw[cd+42:]))
	binary.LittleEndian.PutUint16(result[cd+8:], binary.LittleEndian.Uint16(result[cd+8:])|bit)
	binary.LittleEndian.PutUint16(result[local+6:], binary.LittleEndian.Uint16(result[local+6:])|bit)
	return result
}
func ownedArchiveTestNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}
