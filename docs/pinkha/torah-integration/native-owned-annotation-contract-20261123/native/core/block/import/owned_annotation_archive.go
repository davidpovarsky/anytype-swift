// Byte preparation only: this package-private owner grants no import,
// permission, completion, graph-disposition, body-equality or ACK authority.
package importer

import (
	"archive/zip"
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"unicode"
	"unicode/utf8"

	"github.com/gogo/protobuf/proto"
	descriptor "github.com/gogo/protobuf/protoc-gen-gogo/descriptor"
	"golang.org/x/text/cases"
	"golang.org/x/text/unicode/norm"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	coresb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
)

const (
	ownedArchiveMaxBytes      = 65536
	ownedArchiveMaxMembers    = 512
	ownedArchiveMaxExpanded   = 8 << 20
	ownedArchiveMaxWireDepth  = 64
	ownedArchiveMaxWireFields = 262144
)

// Codes are fixed literals; names, content and wire values are not logged.
func ownedArchiveRefused(code string) error {
	return fmt.Errorf("owned annotation archive refused: %s", code)
}

type ownedAnnotationArchiveMember struct {
	Name           string
	Bytes          uint64
	SHA256         [32]byte
	Kind           string
	ObjectID       string
	SpaceID        string
	SmartBlockType int32
	FileSource     string
	FileID         string
}

type ownedAnnotationArchive struct {
	raw       []byte
	digest    [32]byte
	members   []ownedAnnotationArchiveMember
	snapshots map[string]*pb.SnapshotWithType
	rootID    string
	spaceID   string
}

// Root/Space parameters are exact data comparisons, never authority. Genuine
// generated Snapshot models decode only after bounded ZIP/wire admission.
func inspectOwnedAnnotationArchive(ctx context.Context, raw []byte, expected [32]byte, rootID, spaceID string) (*ownedAnnotationArchive, error) {
	if ctx == nil || rootID == "" || spaceID == "" {
		return nil, ownedArchiveRefused("missing_input")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(raw) < 22 || len(raw) > ownedArchiveMaxBytes {
		return nil, ownedArchiveRefused("compressed_budget")
	}
	frozen := bytes.Clone(raw)
	digest := sha256.Sum256(frozen)
	if digest != expected {
		return nil, ownedArchiveRefused("digest_mismatch")
	}
	layout, err := ownedArchiveLayout(frozen)
	if err != nil {
		return nil, err
	}
	reader, err := zip.NewReader(bytes.NewReader(frozen), int64(len(frozen)))
	if err != nil {
		return nil, ownedArchiveRefused("zip_reader")
	}
	if len(reader.File) != len(layout) {
		return nil, ownedArchiveRefused("zip_inventory")
	}
	wire, err := newOwnedArchiveWireAdmission()
	if err != nil {
		return nil, err
	}
	result := &ownedAnnotationArchive{raw: frozen, digest: digest, rootID: rootID, spaceID: spaceID,
		snapshots: make(map[string]*pb.SnapshotWithType)}
	binaries := make(map[string]bool)
	requiredFiles := make(map[string]bool)
	ids := make(map[string]bool)
	var expanded uint64
	for i, file := range reader.File {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		entry := layout[i]
		offset, offsetErr := file.DataOffset()
		if offsetErr != nil || offset != int64(entry.dataOffset) || file.Name != entry.name ||
			file.CRC32 != entry.crc || file.CompressedSize64 != uint64(entry.compressed) ||
			file.UncompressedSize64 != uint64(entry.expanded) || !file.Mode().IsRegular() {
			return nil, ownedArchiveRefused("zip_member_mismatch")
		}
		if uint64(entry.expanded) > ownedArchiveMaxExpanded-expanded {
			return nil, ownedArchiveRefused("expanded_budget")
		}
		stream, err := file.Open()
		if err != nil {
			return nil, ownedArchiveRefused("zip_member_open")
		}
		body, readErr := io.ReadAll(io.LimitReader(stream, int64(ownedArchiveMaxExpanded-expanded)+1))
		closeErr := stream.Close()
		if readErr != nil || closeErr != nil || uint64(len(body)) != uint64(entry.expanded) {
			return nil, ownedArchiveRefused("zip_member_crc_or_size")
		}
		expanded += uint64(len(body))
		if expanded > ownedArchiveMaxExpanded {
			return nil, ownedArchiveRefused("expanded_budget")
		}
		member := ownedAnnotationArchiveMember{Name: entry.name, Bytes: uint64(len(body)), SHA256: sha256.Sum256(body)}
		parts := strings.Split(entry.name, "/")
		if len(parts) == 2 && parts[0] == "files" {
			member.Kind = "file"
			binaries[entry.name] = true
			result.members = append(result.members, member)
			continue
		}
		if len(parts) != 2 || !strings.HasSuffix(parts[1], ".pb") {
			return nil, ownedArchiveRefused("unsupported_member")
		}
		if _, err := wire.message(ctx, body, ".anytype.SnapshotWithType", 0); err != nil {
			return nil, err
		}
		snapshot := &pb.SnapshotWithType{}
		if err := snapshot.Unmarshal(body); err != nil || snapshot.Snapshot == nil || snapshot.Snapshot.Data == nil || snapshot.Snapshot.Data.Details == nil {
			return nil, ownedArchiveRefused("generated_snapshot")
		}
		data := snapshot.Snapshot.Data
		details := domain.NewDetailsFromProto(data.Details)
		member.Kind = "snapshot"
		member.ObjectID = details.GetString(bundle.RelationKeyId)
		member.SpaceID = details.GetString(bundle.RelationKeySpaceId)
		member.SmartBlockType = int32(snapshot.SbType)
		if member.ObjectID == "" || member.SpaceID != spaceID || parts[1] != member.ObjectID+".pb" || ids[norm.NFC.String(member.ObjectID)] {
			return nil, ownedArchiveRefused("snapshot_identity")
		}
		ids[norm.NFC.String(member.ObjectID)] = true
		if parts[0] != ownedArchiveSnapshotDirectory(coresb.SmartBlockType(snapshot.SbType)) {
			return nil, ownedArchiveRefused("snapshot_directory")
		}
		if coresb.SmartBlockType(snapshot.SbType) == coresb.SmartBlockTypeFileObject {
			member.FileSource = details.GetString(bundle.RelationKeySource)
			if data.FileInfo == nil || data.FileInfo.FileId == "" || !ownedArchiveFileSource(member.FileSource) {
				return nil, ownedArchiveRefused("file_source")
			}
			member.FileID = data.FileInfo.FileId
			requiredFiles[member.FileSource] = true
		}
		result.snapshots[member.ObjectID] = snapshot
		result.members = append(result.members, member)
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if result.snapshots[rootID] == nil {
		return nil, ownedArchiveRefused("missing_root")
	}
	if len(requiredFiles) != len(binaries) {
		return nil, ownedArchiveRefused("file_inventory")
	}
	for name := range requiredFiles {
		if !binaries[name] {
			return nil, ownedArchiveRefused("file_inventory")
		}
	}
	sort.Slice(result.members, func(i, j int) bool { return result.members[i].Name < result.members[j].Name })
	return result, nil
}

func ownedArchiveSnapshotDirectory(kind coresb.SmartBlockType) string {
	switch kind {
	case coresb.SmartBlockTypeRelation:
		return "relations"
	case coresb.SmartBlockTypeRelationOption:
		return "relationsOptions"
	case coresb.SmartBlockTypeObjectType:
		return "types"
	case coresb.SmartBlockTypeTemplate:
		return "templates"
	case coresb.SmartBlockTypeFile, coresb.SmartBlockTypeFileObject:
		return "filesObjects"
	default:
		return "objects"
	}
}
func ownedArchiveFileSource(name string) bool {
	parts := strings.Split(name, "/")
	return len(parts) == 2 && parts[0] == "files" && ownedArchiveSafeName(name)
}
func ownedArchiveSafeName(name string) bool {
	if name == "" || len(name) > 1024 || !utf8.ValidString(name) || strings.HasPrefix(name, "/") || strings.ContainsAny(name, "\\:") {
		return false
	}
	for _, c := range name {
		if unicode.IsControl(c) {
			return false
		}
	}
	for _, part := range strings.Split(name, "/") {
		if part == "" || part == "." || part == ".." || strings.TrimRight(part, ". ") != part {
			return false
		}
	}
	return true
}
func (a *ownedAnnotationArchive) inventory() []ownedAnnotationArchiveMember {
	return append([]ownedAnnotationArchiveMember(nil), a.members...)
}

type ownedArchiveZipEntry struct {
	name        string
	flags       uint16
	method      uint16
	crc         uint32
	compressed  uint32
	expanded    uint32
	localOffset uint32
	dataOffset  uint32
}

// Exact ordinary central/local framing, including authentic Go ZIP data
// descriptors. SFX, ZIP64, hidden/overlapping ranges, encryption, alternate-path
// extras, comments and trailing bytes are outside this bounded input policy.
func ownedArchiveLayout(raw []byte) ([]ownedArchiveZipEntry, error) {
	bad := func() ([]ownedArchiveZipEntry, error) { return nil, ownedArchiveRefused("zip_framing") }
	if len(raw) < 22 {
		return bad()
	}
	u16 := binary.LittleEndian.Uint16
	u32 := binary.LittleEndian.Uint32
	end := raw[len(raw)-22:]
	if u32(end) != 0x06054b50 || u16(end[4:]) != 0 || u16(end[6:]) != 0 || u16(end[20:]) != 0 || u16(end[8:]) != u16(end[10:]) {
		return bad()
	}
	count := int(u16(end[10:]))
	if count == 0 || count > ownedArchiveMaxMembers {
		return bad()
	}
	cdStart, cdBytes := uint64(u32(end[16:])), uint64(u32(end[12:]))
	if cdStart+cdBytes != uint64(len(raw)-22) || cdStart > uint64(len(raw)) {
		return bad()
	}
	cursor := int(cdStart)
	entries := make([]ownedArchiveZipEntry, 0, count)
	names := make(map[string]bool)
	for range count {
		if cursor+46 > len(raw)-22 || u32(raw[cursor:]) != 0x02014b50 {
			return bad()
		}
		h := raw[cursor:]
		nameLen, extraLen, commentLen := int(u16(h[28:])), int(u16(h[30:])), int(u16(h[32:]))
		size := 46 + nameLen + extraLen + commentLen
		if size > len(raw)-22-cursor || commentLen != 0 || u16(h[34:]) != 0 || u16(h[6:]) > 20 {
			return bad()
		}
		entry := ownedArchiveZipEntry{name: string(h[46 : 46+nameLen]), flags: u16(h[8:]), method: u16(h[10:]),
			crc: u32(h[16:]), compressed: u32(h[20:]), expanded: u32(h[24:]), localOffset: u32(h[42:])}
		if entry.flags & ^uint16(0x080e) != 0 || (entry.method != zip.Store && entry.method != zip.Deflate) ||
			(entry.method == zip.Store && entry.flags&6 != 0) || entry.compressed == math.MaxUint32 || entry.expanded == math.MaxUint32 ||
			!ownedArchiveSafeName(entry.name) || !ownedArchiveExtras(h[46+nameLen:46+nameLen+extraLen]) {
			return bad()
		}
		key := cases.Fold().String(norm.NFC.String(entry.name))
		if names[key] {
			return nil, ownedArchiveRefused("zip_duplicate_path")
		}
		names[key] = true
		entries = append(entries, entry)
		cursor += size
	}
	if cursor != len(raw)-22 {
		return bad()
	}
	order := make([]int, len(entries))
	for i := range order {
		order[i] = i
	}
	sort.Slice(order, func(i, j int) bool { return entries[order[i]].localOffset < entries[order[j]].localOffset })
	next := uint64(0)
	for _, i := range order {
		entry := &entries[i]
		start := uint64(entry.localOffset)
		if start != next || start+30 > cdStart {
			return bad()
		}
		h := raw[int(start):]
		if u32(h) != 0x04034b50 || u16(h[4:]) > 20 || u16(h[6:]) != entry.flags || u16(h[8:]) != entry.method {
			return bad()
		}
		nameLen, extraLen := uint64(u16(h[26:])), uint64(u16(h[28:]))
		dataOffset := start + 30 + nameLen + extraLen
		dataEnd := dataOffset + uint64(entry.compressed)
		if dataOffset > cdStart || dataEnd > cdStart || string(h[30:30+nameLen]) != entry.name ||
			!ownedArchiveExtras(h[30+nameLen:30+nameLen+extraLen]) {
			return bad()
		}
		entry.dataOffset = uint32(dataOffset)
		if entry.flags&8 == 0 {
			if u32(h[14:]) != entry.crc || u32(h[18:]) != entry.compressed || u32(h[22:]) != entry.expanded {
				return bad()
			}
			next = dataEnd
		} else {
			if (u32(h[14:]) != 0 && u32(h[14:]) != entry.crc) || (u32(h[18:]) != 0 && u32(h[18:]) != entry.compressed) ||
				(u32(h[22:]) != 0 && u32(h[22:]) != entry.expanded) {
				return bad()
			}
			if dataEnd+12 > cdStart {
				return bad()
			}
			descriptorStart := dataEnd
			if u32(raw[int(descriptorStart):]) == 0x08074b50 {
				descriptorStart += 4
			}
			if descriptorStart+12 > cdStart {
				return bad()
			}
			d := raw[int(descriptorStart):]
			if u32(d) != entry.crc || u32(d[4:]) != entry.compressed || u32(d[8:]) != entry.expanded {
				return bad()
			}
			next = descriptorStart + 12
		}
	}
	if next != cdStart {
		return bad()
	}
	return entries, nil
}

// Original Go exporter metadata is an extended timestamp. Unknown extras are
// not silently interpreted by a future extraction implementation.
func ownedArchiveExtras(extra []byte) bool {
	seen := false
	for len(extra) > 0 {
		if len(extra) < 4 {
			return false
		}
		tag, size := binary.LittleEndian.Uint16(extra), int(binary.LittleEndian.Uint16(extra[2:]))
		if size > len(extra)-4 || tag != 0x5455 || seen || size < 5 || (size-1)%4 != 0 {
			return false
		}
		if extra[4]&^byte(7) != 0 {
			return false
		}
		seen = true
		extra = extra[4+size:]
	}
	return true
}

type ownedArchiveWireAdmission struct {
	messages  map[string]*descriptor.DescriptorProto
	enums     map[string]map[int32]bool
	remaining int
}

// Only original generated descriptors determine field/oneof/map structure.
// This scanner does not replace the original generated Snapshot decoder.
func newOwnedArchiveWireAdmission() (*ownedArchiveWireAdmission, error) {
	v := &ownedArchiveWireAdmission{messages: make(map[string]*descriptor.DescriptorProto),
		enums: make(map[string]map[int32]bool), remaining: ownedArchiveMaxWireFields}
	seen := make(map[string]bool)
	var indexEnums func(string, []*descriptor.EnumDescriptorProto)
	indexEnums = func(prefix string, entries []*descriptor.EnumDescriptorProto) {
		for _, e := range entries {
			values := make(map[int32]bool)
			for _, value := range e.Value {
				values[value.GetNumber()] = true
			}
			v.enums[prefix+"."+e.GetName()] = values
		}
	}
	var indexMessages func(string, []*descriptor.DescriptorProto)
	indexMessages = func(prefix string, entries []*descriptor.DescriptorProto) {
		for _, m := range entries {
			name := prefix + "." + m.GetName()
			v.messages[name] = m
			indexEnums(name, m.EnumType)
			indexMessages(name, m.NestedType)
		}
	}
	var load func(string) error
	load = func(name string) error {
		if seen[name] {
			return nil
		}
		seen[name] = true
		raw := proto.FileDescriptor(name)
		if len(raw) == 0 {
			return ownedArchiveRefused("generated_descriptor_missing")
		}
		gz, err := gzip.NewReader(bytes.NewReader(raw))
		if err != nil {
			return ownedArchiveRefused("generated_descriptor")
		}
		body, readErr := io.ReadAll(io.LimitReader(gz, 16<<20))
		closeErr := gz.Close()
		if readErr != nil || closeErr != nil || len(body) >= 16<<20 {
			return ownedArchiveRefused("generated_descriptor")
		}
		file := &descriptor.FileDescriptorProto{}
		if err := proto.Unmarshal(body, file); err != nil {
			return ownedArchiveRefused("generated_descriptor")
		}
		prefix := "." + file.GetPackage()
		indexMessages(prefix, file.MessageType)
		indexEnums(prefix, file.EnumType)
		for _, dependency := range file.Dependency {
			if err := load(dependency); err != nil {
				return err
			}
		}
		return nil
	}
	if err := load("pb/protos/snapshot.proto"); err != nil {
		return nil, err
	}
	return v, nil
}

type ownedArchiveWireField struct {
	number  int32
	wire    uint64
	value   uint64
	payload []byte
}

func ownedArchiveVarint(raw []byte) (uint64, int, error) {
	value, n := binary.Uvarint(raw)
	if n <= 0 || (n > 1 && value < uint64(1)<<uint(7*(n-1))) {
		return 0, 0, ownedArchiveRefused("wire_varint")
	}
	return value, n, nil
}
func ownedArchiveReadField(raw []byte) (ownedArchiveWireField, int, error) {
	var f ownedArchiveWireField
	tag, n, err := ownedArchiveVarint(raw)
	if err != nil {
		return f, 0, err
	}
	if tag>>3 == 0 || tag>>3 > (1<<29)-1 {
		return f, 0, ownedArchiveRefused("wire_tag")
	}
	f.number, f.wire = int32(tag>>3), tag&7
	cursor := n
	switch f.wire {
	case 0:
		f.value, n, err = ownedArchiveVarint(raw[cursor:])
		cursor += n
	case 1:
		if len(raw)-cursor < 8 {
			return f, 0, ownedArchiveRefused("wire_fixed")
		}
		f.payload = raw[cursor : cursor+8]
		cursor += 8
	case 2:
		var length uint64
		length, n, err = ownedArchiveVarint(raw[cursor:])
		cursor += n
		if err == nil {
			if length > uint64(len(raw)-cursor) {
				return f, 0, ownedArchiveRefused("wire_length")
			}
			f.payload = raw[cursor : cursor+int(length)]
			cursor += int(length)
		}
	case 5:
		if len(raw)-cursor < 4 {
			return f, 0, ownedArchiveRefused("wire_fixed")
		}
		f.payload = raw[cursor : cursor+4]
		cursor += 4
	default:
		return f, 0, ownedArchiveRefused("wire_type")
	}
	return f, cursor, err
}
func ownedArchiveExpectedWire(kind descriptor.FieldDescriptorProto_Type) uint64 {
	switch kind {
	case descriptor.FieldDescriptorProto_TYPE_DOUBLE, descriptor.FieldDescriptorProto_TYPE_FIXED64, descriptor.FieldDescriptorProto_TYPE_SFIXED64:
		return 1
	case descriptor.FieldDescriptorProto_TYPE_STRING, descriptor.FieldDescriptorProto_TYPE_BYTES, descriptor.FieldDescriptorProto_TYPE_MESSAGE:
		return 2
	case descriptor.FieldDescriptorProto_TYPE_FLOAT, descriptor.FieldDescriptorProto_TYPE_FIXED32, descriptor.FieldDescriptorProto_TYPE_SFIXED32:
		return 5
	default:
		return 0
	}
}
func (v *ownedArchiveWireAdmission) scalar(f ownedArchiveWireField, declared *descriptor.FieldDescriptorProto) error {
	kind := declared.GetType()
	if f.wire != ownedArchiveExpectedWire(kind) || kind == descriptor.FieldDescriptorProto_TYPE_GROUP {
		return ownedArchiveRefused("wire_schema_type")
	}
	switch kind {
	case descriptor.FieldDescriptorProto_TYPE_STRING:
		if !utf8.Valid(f.payload) {
			return ownedArchiveRefused("wire_utf8")
		}
	case descriptor.FieldDescriptorProto_TYPE_BOOL:
		if f.value > 1 {
			return ownedArchiveRefused("wire_bool")
		}
	case descriptor.FieldDescriptorProto_TYPE_UINT32, descriptor.FieldDescriptorProto_TYPE_SINT32:
		if f.value > math.MaxUint32 {
			return ownedArchiveRefused("wire_integer")
		}
	case descriptor.FieldDescriptorProto_TYPE_INT32, descriptor.FieldDescriptorProto_TYPE_ENUM:
		signed := int32(f.value)
		if f.value != uint64(int64(signed)) {
			return ownedArchiveRefused("wire_integer")
		}
		if kind == descriptor.FieldDescriptorProto_TYPE_ENUM && !v.enums[declared.GetTypeName()][signed] {
			return ownedArchiveRefused("wire_unknown_enum")
		}
	case descriptor.FieldDescriptorProto_TYPE_DOUBLE:
		value := math.Float64frombits(binary.LittleEndian.Uint64(f.payload))
		if math.IsNaN(value) || math.IsInf(value, 0) {
			return ownedArchiveRefused("wire_nonfinite")
		}
	case descriptor.FieldDescriptorProto_TYPE_FLOAT:
		value := float64(math.Float32frombits(binary.LittleEndian.Uint32(f.payload)))
		if math.IsNaN(value) || math.IsInf(value, 0) {
			return ownedArchiveRefused("wire_nonfinite")
		}
	}
	return nil
}
func (v *ownedArchiveWireAdmission) message(ctx context.Context, raw []byte, name string, depth int) (string, error) {
	if err := ctx.Err(); err != nil {
		return "", err
	}
	desc := v.messages[name]
	if desc == nil || depth > ownedArchiveMaxWireDepth {
		return "", ownedArchiveRefused("wire_message_or_depth")
	}
	fields := make(map[int32]*descriptor.FieldDescriptorProto, len(desc.Field))
	for _, field := range desc.Field {
		fields[field.GetNumber()] = field
	}
	seen := make(map[int32]bool)
	oneofs := make(map[int32]bool)
	maps := make(map[int32]map[string]bool)
	mapKey := ""
	if desc.GetOptions().GetMapEntry() {
		key := fields[1]
		if key == nil || key.GetType() != descriptor.FieldDescriptorProto_TYPE_STRING {
			return "", ownedArchiveRefused("wire_unsupported_map_key")
		}
	}
	for len(raw) > 0 {
		v.remaining--
		if v.remaining < 0 {
			return "", ownedArchiveRefused("wire_budget")
		}
		f, used, err := ownedArchiveReadField(raw)
		if err != nil {
			return "", err
		}
		raw = raw[used:]
		field := fields[f.number]
		if field == nil {
			return "", ownedArchiveRefused("wire_unknown_field")
		}
		repeated := field.GetLabel() == descriptor.FieldDescriptorProto_LABEL_REPEATED
		if !repeated && seen[f.number] {
			return "", ownedArchiveRefused("wire_duplicate_singular")
		}
		seen[f.number] = true
		if field.OneofIndex != nil {
			if oneofs[field.GetOneofIndex()] {
				return "", ownedArchiveRefused("wire_duplicate_oneof")
			}
			oneofs[field.GetOneofIndex()] = true
		}
		expectedWire := ownedArchiveExpectedWire(field.GetType())
		if repeated && f.wire == 2 && expectedWire != 2 {
			packed := f.payload
			for len(packed) > 0 {
				v.remaining--
				if v.remaining < 0 {
					return "", ownedArchiveRefused("wire_budget")
				}
				item := ownedArchiveWireField{wire: expectedWire}
				var n int
				switch expectedWire {
				case 0:
					item.value, n, err = ownedArchiveVarint(packed)
				case 1:
					n = 8
				case 5:
					n = 4
				default:
					return "", ownedArchiveRefused("wire_packed")
				}
				if err != nil || n > len(packed) {
					return "", ownedArchiveRefused("wire_packed")
				}
				if expectedWire != 0 {
					item.payload = packed[:n]
				}
				if err := v.scalar(item, field); err != nil {
					return "", err
				}
				packed = packed[n:]
			}
			continue
		}
		if err := v.scalar(f, field); err != nil {
			return "", err
		}
		if desc.GetOptions().GetMapEntry() && f.number == 1 {
			mapKey = norm.NFC.String(string(f.payload))
		}
		if field.GetType() == descriptor.FieldDescriptorProto_TYPE_MESSAGE {
			key, err := v.message(ctx, f.payload, field.GetTypeName(), depth+1)
			if err != nil {
				return "", err
			}
			child := v.messages[field.GetTypeName()]
			if child.GetOptions().GetMapEntry() {
				if maps[f.number] == nil {
					maps[f.number] = make(map[string]bool)
				}
				if maps[f.number][key] {
					return "", ownedArchiveRefused("wire_duplicate_map_key")
				}
				maps[f.number][key] = true
			}
		}
	}
	return mapKey, nil
}

type ownedAnnotationArchiveStaging struct {
	root           string
	archivePath    string
	extractionRoot string
	digest         [32]byte
	closeOnce      sync.Once
	closeErr       error
}

// No caller-chosen path is accepted. One exclusive archive and a separate
// extraction directory live inside a newly owned 0700 root. No native importer
// is started and no file-provider replacement is installed by this slice.
func (a *ownedAnnotationArchive) stage(ctx context.Context) (staged *ownedAnnotationArchiveStaging, err error) {
	if a == nil || ctx == nil || len(a.raw) == 0 || sha256.Sum256(a.raw) != a.digest {
		return nil, ownedArchiveRefused("staging_source")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	root, err := os.MkdirTemp("", "anytype-owned-annotation-")
	if err != nil {
		return nil, err
	}
	owner := &ownedAnnotationArchiveStaging{root: root, archivePath: filepath.Join(root, "archive.zip"),
		extractionRoot: filepath.Join(root, "extracted"), digest: a.digest}
	ok := false
	defer func() {
		if !ok {
			err = errors.Join(err, owner.Close())
		}
	}()
	if err := os.Chmod(root, 0700); err != nil {
		return nil, err
	}
	if err := os.Mkdir(owner.extractionRoot, 0700); err != nil {
		return nil, err
	}
	file, err := os.OpenFile(owner.archivePath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return nil, err
	}
	n, writeErr := file.Write(a.raw)
	syncErr := file.Sync()
	closeErr := file.Close()
	if err := errors.Join(writeErr, syncErr, closeErr); err != nil {
		return nil, err
	}
	if n != len(a.raw) {
		return nil, io.ErrShortWrite
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	ok = true
	return owner, nil
}
func (s *ownedAnnotationArchiveStaging) TempDir() string { return s.extractionRoot }
func (s *ownedAnnotationArchiveStaging) Close() error {
	if s == nil {
		return nil
	}
	s.closeOnce.Do(func() { s.closeErr = os.RemoveAll(s.root) })
	return s.closeErr
}
