//go:build pinkha_loaded_account_witness

package application

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"

	nativeexport "github.com/anyproto/anytype-heart/core/block/export"
	"github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
	"github.com/anyproto/anytype-heart/pkg/lib/anyblockjson/storeresolver"
)

// The private bundle retains native identifiers, raw metadata, encryption
// metadata and history. It is never a public result/artifact.
type NativeSourceMember struct {
	Path, SHA256 string
	Bytes        int64
}
type NativeSourceObjectMember struct {
	ObjectID, UniqueKey string
	NativeType          int32
	Snapshot            NativeSourceMember
	NativeJSONView      NativeSourceMember
}
type NativeSourceFileVariantMember struct {
	Path, ContentID, MetadataID, Name, MIME, NativeChecksum, SourceChecksum string
	NativeOriginalPath, UploadChecksumMatches                               bool
	Payload, Metadata                                                       NativeSourceMember
}
type NativeSourceFileMember struct {
	FileID   string
	Variants []NativeSourceFileVariantMember
}
type NativeSourceBundleManifest struct {
	Contract                 string
	Receipt                  LoadedAccountSpaceWitnessReceipt
	SourceRows               NativeSourceMember
	Trees                    []NativeSourceTree
	Objects                  []NativeSourceObjectMember
	Files                    []NativeSourceFileMember
	FileReferences           []nativeexport.NativeFileReference
	Gaps                     []NativeSourceGap
	ResolverUnmapped         []storeresolver.UnmappedReference
	BundledDefinitionsUsed   []string
	RetainedOtherCollections []localstorewitness.NativeRetainedCollection
}

func (w *LoadedAccountSpaceWitness) PrivateBundleDirectory() string {
	if w == nil || !w.complete {
		return ""
	}
	return w.privateDirectory
}

func nativeSourceWriteMember(directory, name string, write func(io.Writer) error) (NativeSourceMember, error) {
	if name == "" || filepath.Base(name) != name {
		return NativeSourceMember{}, ErrLoadedAccountSpaceWitness
	}
	path := filepath.Join(directory, name)
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return NativeSourceMember{}, err
	}
	hash := sha256.New()
	err = write(io.MultiWriter(file, hash))
	stat, statErr := file.Stat()
	err = errors.Join(err, statErr, file.Sync(), file.Close())
	if err != nil {
		return NativeSourceMember{}, err
	}
	if err = os.Chmod(path, 0400); err != nil {
		return NativeSourceMember{}, err
	}
	return NativeSourceMember{Path: name, SHA256: hex.EncodeToString(hash.Sum(nil)), Bytes: stat.Size()}, nil
}

func (w *LoadedAccountSpaceWitness) writePrivateBundle() error {
	receipt, err := w.Receipt()
	if err != nil {
		return err
	}
	manifest := NativeSourceBundleManifest{
		Contract: "pinkha-native-whole-source-bundle-v1", Receipt: receipt, Trees: w.Trees(),
		FileReferences: w.FileReferences(), Gaps: w.Gaps(), ResolverUnmapped: w.ResolverUnmapped(),
		RetainedOtherCollections: w.inventory.RetainedOtherCollections(),
	}
	if w.resolver != nil {
		manifest.BundledDefinitionsUsed = w.resolver.BundledDefinitionsUsed()
	}
	manifest.SourceRows, err = nativeSourceWriteMember(w.privateDirectory, "native-source-rows.witness", w.PrivateWitness().WritePrivate)
	if err != nil {
		return err
	}
	var totalJSONBytes int64
	for _, object := range w.objects {
		raw := object.SnapshotBase()
		member, err := nativeSourceWriteMember(w.privateDirectory, "snapshot-"+loadedAccountWitnessHash(object.ObjectID())+".pb",
			func(dst io.Writer) error { _, e := io.Copy(dst, bytes.NewReader(raw)); return e })
		if err != nil {
			return err
		}
		view, err := object.JSONView()
		if err != nil {
			return err
		}
		totalJSONBytes += int64(len(view))
		if totalJSONBytes > 256<<20 {
			return ErrLoadedAccountSpaceWitness
		}
		viewMember, err := nativeSourceWriteMember(w.privateDirectory, "snapshot-"+loadedAccountWitnessHash(object.ObjectID())+".json",
			func(dst io.Writer) error { _, e := io.Copy(dst, bytes.NewReader(view)); return e })
		if err != nil {
			return err
		}
		manifest.Objects = append(manifest.Objects, NativeSourceObjectMember{ObjectID: object.ObjectID(), UniqueKey: object.UniqueKey(), NativeType: int32(object.Type()), Snapshot: member, NativeJSONView: viewMember})
	}
	for _, id := range w.fileIDs {
		member := NativeSourceFileMember{FileID: id}
		for _, variant := range w.files[id].Variants() {
			raw := variant.Metadata()
			metadata, err := nativeSourceWriteMember(w.privateDirectory, "metadata-"+loadedAccountWitnessHash(id+"\x00"+variant.Path())+".pb",
				func(dst io.Writer) error { _, e := io.Copy(dst, bytes.NewReader(raw)); return e })
			if err != nil {
				return err
			}
			file, err := variant.Open()
			if err != nil {
				return err
			}
			hash := sha256.New()
			count, copyErr := io.Copy(hash, file)
			closeErr := file.Close()
			if copyErr != nil || closeErr != nil || count != variant.Size() || hex.EncodeToString(hash.Sum(nil)) != variant.ContentSHA256() {
				return errors.Join(ErrLoadedAccountSpaceWitness, copyErr, closeErr)
			}
			payload := NativeSourceMember{Path: filepath.ToSlash(filepath.Join(loadedAccountWitnessHash(id), loadedAccountWitnessHash(id+"\x00"+variant.Path())+".payload")), Bytes: count, SHA256: variant.ContentSHA256()}
			member.Variants = append(member.Variants, NativeSourceFileVariantMember{
				Path: variant.Path(), ContentID: variant.ContentID(), MetadataID: variant.MetadataID(), Name: variant.Name(), MIME: variant.MIME(),
				NativeChecksum: variant.NativeChecksum(), SourceChecksum: variant.SourceChecksum(),
				NativeOriginalPath: variant.Original(), UploadChecksumMatches: variant.UploadChecksumMatches(),
				Payload: payload, Metadata: metadata,
			})
		}
		manifest.Files = append(manifest.Files, member)
	}
	_, err = nativeSourceWriteMember(w.privateDirectory, "manifest.json", func(dst io.Writer) error {
		encoder := json.NewEncoder(dst)
		encoder.SetIndent("", "  ")
		return encoder.Encode(manifest)
	})
	return err
}
