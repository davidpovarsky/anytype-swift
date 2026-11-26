// Command recovered-compiled-definitions reads seven original native registry
// entries. It never opens an account, space, service, store, or network endpoint.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/gogo/protobuf/jsonpb"
	"github.com/gogo/protobuf/proto"
)

var requiredKeys = []string{
	"analyticsSpaceId",
	"apiObjectKey",
	"headerRelationsLayout",
	"homepage",
	"migrationObjectContext",
	"orderId",
	"relationFormatIncludeTime",
}

type member struct {
	Path   string
	SHA256 string
	Bytes  int
}
type descriptor struct {
	Kind            string
	Key             string
	ProtobufMessage string
	Protobuf        member
	JSONView        member
}
type jsonView struct {
	Contract        string
	Kind            string
	Key             string
	ProtobufMessage string
	ProtobufSHA256  string
	ProtobufBytes   int
	Definition      json.RawMessage
}
type result struct {
	Contract                     string
	Origin                       string
	Descriptors                  []descriptor
	ProtobufDecodeEqualsRegistry bool
	JSONDecodeEqualsRegistry     bool
	RegistryUnchangedAfterExport bool
	OriginalCapturedMember       bool
	AccountOrSpaceOpened         bool
	DestinationWrites            bool
}

func digest(raw []byte) string {
	value := sha256.Sum256(raw)
	return hex.EncodeToString(value[:])
}
func writeMember(root, name string, raw []byte) (member, error) {
	if len(raw) == 0 || len(raw) > 4*1024*1024 || filepath.Base(name) != name {
		return member{}, errors.New("invalid bounded member")
	}
	p := filepath.Join(root, name)
	f, err := os.OpenFile(p, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return member{}, err
	}
	_, writeErr := f.Write(raw)
	syncErr := f.Sync()
	closeErr := f.Close()
	if writeErr != nil {
		return member{}, writeErr
	}
	if syncErr != nil {
		return member{}, syncErr
	}
	if closeErr != nil {
		return member{}, closeErr
	}
	readback, err := os.ReadFile(p)
	if err != nil || !bytes.Equal(readback, raw) {
		return member{}, errors.New("member readback mismatch")
	}
	return member{Path: name, SHA256: digest(raw), Bytes: len(raw)}, nil
}
func run() error {
	if len(os.Args) != 2 || !filepath.IsAbs(os.Args[1]) {
		return errors.New("one new absolute output directory required")
	}
	if _, exists := os.LookupEnv("ANYTYPE_EXTRA_RELATIONS"); exists {
		return errors.New("extra-registry environment must be absent")
	}
	root := filepath.Clean(os.Args[1])
	if root != os.Args[1] {
		return errors.New("canonical output path required")
	}
	parent, err := filepath.EvalSymlinks(filepath.Dir(root))
	if err != nil || parent != filepath.Dir(root) {
		return errors.New("canonical existing output parent required")
	}
	if err := os.Mkdir(root, 0700); err != nil {
		return err
	}
	out := result{
		Contract:                     "pinkha-recovered-compiled-definition-export-v1",
		Origin:                       "original-source-registry-recovery-not-historical-captured-members",
		ProtobufDecodeEqualsRegistry: true, JSONDecodeEqualsRegistry: true,
		RegistryUnchangedAfterExport: true,
	}
	marshaler := jsonpb.Marshaler{OrigName: true, EmitDefaults: false, EnumsAsInts: true}
	for _, key := range requiredKeys {
		original, err := bundle.GetRelation(domain.RelationKey(key))
		if err != nil || original == nil || original.Key != key || original.Id != "_br"+key {
			return fmt.Errorf("original registry identity refused: %s", key)
		}
		if proto.MessageName(original) != "anytype.model.Relation" {
			return errors.New("original generated protobuf message mismatch")
		}
		// Keep the first bytes emitted by the original generated wire codec.
		// No deterministic Buffer or replacement protobuf encoding is imposed.
		wire, err := proto.Marshal(original)
		if err != nil || len(wire) == 0 || len(wire) > 1024*1024 {
			return errors.New("original protobuf serialization failed")
		}
		decoded := new(model.Relation)
		if err := proto.Unmarshal(wire, decoded); err != nil || !proto.Equal(original, decoded) {
			return errors.New("full original wire decode differs from registry")
		}
		view, err := marshaler.MarshalToString(original)
		if err != nil {
			return err
		}
		viewAgain, err := marshaler.MarshalToString(decoded)
		if err != nil || view != viewAgain {
			return errors.New("generated JSON view differs after complete wire decode")
		}
		jsonDecoded := new(model.Relation)
		if err := jsonpb.UnmarshalString(view, jsonDecoded); err != nil || !proto.Equal(original, jsonDecoded) {
			return errors.New("complete generated JSON decode differs from registry")
		}
		current, err := bundle.GetRelation(domain.RelationKey(key))
		if err != nil || !proto.Equal(original, current) {
			return errors.New("original registry changed during export")
		}
		identity := digest([]byte("property:" + key))
		pb, err := writeMember(root, identity+".pb", wire)
		if err != nil {
			return err
		}
		envelope, err := json.Marshal(jsonView{
			Contract: "pinkha-native-bundled-definition-json-v1",
			Kind:     "property", Key: key, ProtobufMessage: "anytype.model.Relation",
			ProtobufSHA256: digest(wire), ProtobufBytes: len(wire),
			Definition: json.RawMessage(view),
		})
		if err != nil {
			return err
		}
		js, err := writeMember(root, identity+".json", envelope)
		if err != nil {
			return err
		}
		out.Descriptors = append(out.Descriptors, descriptor{
			Kind: "property", Key: key, ProtobufMessage: "anytype.model.Relation",
			Protobuf: pb, JSONView: js,
		})
	}
	raw, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		return err
	}
	_, err = writeMember(root, "export.json", append(raw, '\n'))
	if err != nil {
		return err
	}
	fmt.Printf("RECOVERED_COMPILED_DEFINITIONS descriptors=%d originalCapturedMember=false accountOrSpaceOpened=false destinationWrites=false\n", len(out.Descriptors))
	return nil
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
