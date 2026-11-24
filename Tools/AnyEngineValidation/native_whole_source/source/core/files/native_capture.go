//go:build pinkha_loaded_account_witness

package files

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/anyproto/any-sync/app"
	"github.com/gogo/protobuf/proto"
	uio "github.com/ipfs/boxo/ipld/unixfs/io"
	"github.com/ipfs/go-cid"
	ipld "github.com/ipfs/go-ipld-format"
	"github.com/multiformats/go-base32"

	"github.com/anyproto/anytype-heart/core/files/filehelper"
	"github.com/anyproto/anytype-heart/core/files/fileobject/filemodels"
	"github.com/anyproto/anytype-heart/core/files/filestorage"
	"github.com/anyproto/anytype-heart/pkg/lib/crypto/symmetric"
	"github.com/anyproto/anytype-heart/pkg/lib/mill/schema"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/storage"
)

var ErrNativeFileCapture = errors.New("complete local native file DAG and plaintext capture required")

type NativeFileCaptureLimits struct {
	MaxVariantBytes int64
	MaxTotalBytes   int64
	MaxDAGNodes     int
	MaxDAGBytes     int64
}

func DefaultNativeFileCaptureLimits() NativeFileCaptureLimits {
	return NativeFileCaptureLimits{MaxVariantBytes: 512 << 20, MaxTotalBytes: 1 << 30, MaxDAGNodes: 50000, MaxDAGBytes: 2 << 30}
}

type NativeFileVariant struct {
	path, contentID, metadataID, name, mime, checksum, source, plainSHA, localPath string
	bytes                                                                          int64
	original                                                                       bool
	nativeChecksumVerified                                                         bool
	metadata                                                                       []byte
	fileInfo                                                                       os.FileInfo
}

func (v NativeFileVariant) Path() string           { return v.path }
func (v NativeFileVariant) ContentID() string      { return v.contentID }
func (v NativeFileVariant) MetadataID() string     { return v.metadataID }
func (v NativeFileVariant) Name() string           { return v.name }
func (v NativeFileVariant) MIME() string           { return v.mime }
func (v NativeFileVariant) Size() int64            { return v.bytes }
func (v NativeFileVariant) ContentSHA256() string  { return v.plainSHA }
func (v NativeFileVariant) Original() bool         { return v.original }
func (v NativeFileVariant) NativeChecksum() string { return v.checksum }
func (v NativeFileVariant) SourceChecksum() string { return v.source }

// Metadata returns every original decrypted metadata byte, including extension
// fields and unknown protobuf fields. It never exposes the encryption key in a
// public receipt; this accessor belongs to the private canonical source bundle.
func (v NativeFileVariant) Metadata() []byte { return append([]byte(nil), v.metadata...) }

// Original reports the native original PATH, not an inference from image size.
// UploadChecksumMatches additionally checks the native source checksum against
// the verified checksum of this captured representation.
func (v NativeFileVariant) UploadChecksumMatches() bool {
	return v.original && v.nativeChecksumVerified && v.source != "" && v.source == v.checksum
}

// Open verifies the exact captured spool inode and shape. The destination's
// prepare contract must rehash the reader against ContentSHA256 and exact Size.
func (v NativeFileVariant) Open() (*os.File, error) {
	info, err := os.Lstat(v.localPath)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 || !os.SameFile(info, v.fileInfo) || info.Size() != v.bytes {
		return nil, errors.Join(ErrNativeFileCapture, err)
	}
	file, err := os.Open(v.localPath)
	if err != nil {
		return nil, err
	}
	actual, err := file.Stat()
	if err != nil || !os.SameFile(actual, v.fileInfo) || actual.Size() != v.bytes {
		file.Close()
		return nil, errors.Join(ErrNativeFileCapture, err)
	}
	return file, nil
}

type NativeFileCapture struct {
	fileID   string
	variants []NativeFileVariant
	dagNodes int
	dagBytes int64
	dagSHA   string
	complete bool
}
type NativeFileCaptureReceipt struct {
	Version, FileIDSHA256, DAGInventorySHA256                                   string
	Variants, OriginalVariants, DAGNodes                                        int
	PlaintextBytes, DAGBytes                                                    int64
	MetadataBytes                                                               int
	AllDAGBlocksLocal, AllVariantBytesRead                                      bool
	SourceAccountAuthorized, HasNativeSourceAdmission, PermitsDestinationWrites bool
	VariantReceipts                                                             []NativeFileVariantReceipt
}
type NativeFileVariantReceipt struct {
	PathSHA256, ContentIDSHA256, MetadataIDSHA256, PlaintextSHA256 string
	MetadataSHA256                                                 string
	MetadataBytes                                                  int
	UploadChecksumMatches                                          bool
	Bytes                                                          int64
	Original, NativeChecksumVerified                               bool
}

func (c *NativeFileCapture) FileID() string {
	if c == nil || !c.complete {
		return ""
	}
	return c.fileID
}
func (c *NativeFileCapture) Variants() []NativeFileVariant {
	if c == nil || !c.complete {
		return nil
	}
	return append([]NativeFileVariant(nil), c.variants...)
}
func nativeFileHash(raw []byte) string { sum := sha256.Sum256(raw); return hex.EncodeToString(sum[:]) }
func (c *NativeFileCapture) Receipt() (NativeFileCaptureReceipt, error) {
	if c == nil || !c.complete {
		return NativeFileCaptureReceipt{}, ErrNativeFileCapture
	}
	r := NativeFileCaptureReceipt{Version: "native-local-file-capture-v1", FileIDSHA256: nativeFileHash([]byte(c.fileID)),
		DAGInventorySHA256: c.dagSHA, DAGNodes: c.dagNodes, DAGBytes: c.dagBytes, Variants: len(c.variants),
		AllDAGBlocksLocal: true, AllVariantBytesRead: true}
	for _, v := range c.variants {
		r.PlaintextBytes += v.bytes
		r.MetadataBytes += len(v.metadata)
		if v.original {
			r.OriginalVariants++
		}
		r.VariantReceipts = append(r.VariantReceipts, NativeFileVariantReceipt{
			PathSHA256: nativeFileHash([]byte(v.path)), ContentIDSHA256: nativeFileHash([]byte(v.contentID)),
			MetadataIDSHA256: nativeFileHash([]byte(v.metadataID)), PlaintextSHA256: v.plainSHA, Bytes: v.bytes,
			Original: v.original, NativeChecksumVerified: v.nativeChecksumVerified,
			MetadataSHA256: nativeFileHash(v.metadata), MetadataBytes: len(v.metadata),
			UploadChecksumMatches: v.UploadChecksumMatches()})
	}
	return r, nil
}

type nativeVerifiedDAG struct{ ipld.DAGService }

func (d nativeVerifiedDAG) Get(ctx context.Context, id cid.Cid) (ipld.Node, error) {
	node, err := d.DAGService.Get(ctx, id)
	if err != nil {
		return nil, err
	}
	actual, err := id.Prefix().Sum(node.RawData())
	if err != nil || !actual.Equals(id) || !node.Cid().Equals(id) {
		return nil, errors.Join(ErrNativeFileCapture, err)
	}
	return node, nil
}
func (d nativeVerifiedDAG) GetMany(ctx context.Context, ids []cid.Cid) <-chan *ipld.NodeOption {
	out := make(chan *ipld.NodeOption)
	go func() {
		defer close(out)
		for _, id := range ids {
			node, err := d.Get(ctx, id)
			select {
			case out <- &ipld.NodeOption{Node: node, Err: err}:
			case <-ctx.Done():
				return
			}
		}
	}()
	return out
}

type nativeContextReader struct {
	ctx    context.Context
	reader io.Reader
}

func (r nativeContextReader) Read(p []byte) (int, error) {
	if err := r.ctx.Err(); err != nil {
		return 0, err
	}
	return r.reader.Read(p)
}

func nativeLocalReader(ctx context.Context, dag ipld.DAGService, id cid.Cid, key string) (symmetric.ReadSeekCloser, error) {
	node, err := dag.Get(ctx, id)
	if err != nil {
		return nil, err
	}
	reader, err := uio.NewDagReader(ctx, node, dag)
	if err != nil {
		return nil, err
	}
	if key == "" {
		return reader, nil
	}
	parsed, err := symmetric.FromString(key)
	if err != nil {
		reader.Close()
		return nil, err
	}
	decoder, err := getEncryptorDecryptor(parsed)
	if err != nil {
		reader.Close()
		return nil, err
	}
	plain, err := decoder.DecryptReader(reader)
	if err != nil {
		reader.Close()
		return nil, err
	}
	return plain, nil
}

// CaptureNativeLocalFile receives only the FileInfo from a previously locked
// native object. Its caller must join that snapshot and final native checkpoint
// to current account/session authority. No mutable objectStore lookup or remote
// fetch occurs here; all DAG reads come from the concrete native local store.
func CaptureNativeLocalFile(ctx context.Context, fileComponent, storageComponent app.Component,
	spaceID string, captured *model.FileInfo, privateDirectory string, limits NativeFileCaptureLimits,
) (*NativeFileCapture, error) {
	owner, ok := fileComponent.(*service)
	if ctx == nil || !ok || owner == nil || spaceID == "" || captured == nil || captured.FileId == "" ||
		limits.MaxVariantBytes < 1 || limits.MaxVariantBytes > 512<<20 || limits.MaxTotalBytes < 1 || limits.MaxTotalBytes > 2<<30 ||
		limits.MaxDAGNodes < 1 || limits.MaxDAGNodes > 50000 || limits.MaxDAGBytes < 1 || limits.MaxDAGBytes > 3<<30 {
		return nil, ErrNativeFileCapture
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	info, err := os.Lstat(privateDirectory)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm() != 0700 {
		return nil, errors.Join(ErrNativeFileCapture, err)
	}
	physical, err := filepath.EvalSymlinks(privateDirectory)
	if err != nil || physical != filepath.Clean(privateDirectory) {
		return nil, errors.Join(ErrNativeFileCapture, err)
	}
	local, err := filestorage.NativeSnapshotLocalDAG(storageComponent)
	if err != nil {
		return nil, err
	}
	dag := nativeVerifiedDAG{filehelper.NewDAGServiceWithSpaceID(spaceID, local)}
	rootID, err := cid.Parse(captured.FileId)
	if err != nil {
		return nil, err
	}
	keys := map[string]string{}
	for _, key := range captured.EncryptionKeys {
		if key == nil || key.Path == "" {
			return nil, ErrNativeFileCapture
		}
		if _, exists := keys[key.Path]; exists {
			return nil, ErrNativeFileCapture
		}
		keys[key.Path] = key.Key
	}
	// Walk every branch, including every UnixFS leaf. There is no "first
	// branch" or "largest image" completeness shortcut.
	seen := map[string]bool{}
	queue := []cid.Cid{rootID}
	queued := map[string]bool{rootID.String(): true}
	var dagRows []string
	var dagBytes int64
	for len(queue) > 0 {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		id := queue[0]
		queue = queue[1:]
		if seen[id.String()] {
			continue
		}
		seen[id.String()] = true
		if len(seen) > limits.MaxDAGNodes {
			return nil, ErrNativeFileCapture
		}
		node, err := dag.Get(ctx, id)
		if err != nil {
			return nil, err
		}
		dagBytes += int64(len(node.RawData()))
		if dagBytes > limits.MaxDAGBytes {
			return nil, ErrNativeFileCapture
		}
		dagRows = append(dagRows, id.String()+":"+nativeFileHash(node.RawData()))
		for _, link := range node.Links() {
			if link == nil {
				return nil, ErrNativeFileCapture
			}
			if !queued[link.Cid.String()] {
				if len(queued) >= limits.MaxDAGNodes {
					return nil, ErrNativeFileCapture
				}
				queued[link.Cid.String()] = true
				queue = append(queue, link.Cid)
			}
		}
	}
	root, err := dag.Get(ctx, rootID)
	if err != nil {
		return nil, err
	}
	outer := root.Links()
	if len(outer) != 1 || outer[0].Name != "0" {
		return nil, ErrNativeFileCapture
	}
	inner, err := dag.Get(ctx, outer[0].Cid)
	if err != nil {
		return nil, err
	}
	type pair struct {
		path string
		node ipld.Node
	}
	var pairs []pair
	if looksLikeFileNode(inner) {
		pairs = append(pairs, pair{"/0/", inner})
	} else {
		names := map[string]bool{}
		for _, link := range inner.Links() {
			if link.Name == "" || strings.ContainsAny(link.Name, "/\\") || names[link.Name] {
				return nil, ErrNativeFileCapture
			}
			names[link.Name] = true
			node, err := dag.Get(ctx, link.Cid)
			if err != nil {
				return nil, err
			}
			if !looksLikeFileNode(node) {
				return nil, ErrNativeFileCapture
			}
			pairs = append(pairs, pair{encryptionKeyPath(link.Name), node})
		}
	}
	if len(pairs) == 0 || len(pairs) > 256 {
		return nil, ErrNativeFileCapture
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].path < pairs[j].path })
	capture := &NativeFileCapture{fileID: captured.FileId, dagNodes: len(seen), dagBytes: dagBytes}
	created := []string{}
	success := false
	defer func() {
		if !success {
			for _, path := range created {
				_ = os.Remove(path)
			}
		}
	}()
	usedKeys := map[string]bool{}
	total := int64(0)
	metadataTotal := 0
	for _, entry := range pairs {
		key := keys[entry.path]
		if _, exists := keys[entry.path]; exists {
			usedKeys[entry.path] = true
		}
		metaLink := schema.LinkByName(entry.node.Links(), ValidMetaLinkNames)
		contentLink := schema.LinkByName(entry.node.Links(), ValidContentLinkNames)
		if metaLink == nil || contentLink == nil {
			return nil, ErrNativeFileCapture
		}
		reader, err := nativeLocalReader(ctx, dag, metaLink.Cid, key)
		if err != nil {
			return nil, err
		}
		raw, readErr := io.ReadAll(io.LimitReader(nativeContextReader{ctx, reader}, (1<<20)+1))
		closeErr := reader.Close()
		if readErr != nil || closeErr != nil || len(raw) > 1<<20 {
			return nil, errors.Join(ErrNativeFileCapture, readErr, closeErr)
		}
		metadataTotal += len(raw)
		if metadataTotal > 8<<20 {
			return nil, ErrNativeFileCapture
		}
		meta := new(storage.FileInfo)
		if err := proto.Unmarshal(raw, meta); err != nil {
			return nil, err
		}
		if meta.Hash != contentLink.Cid.String() || meta.Key != key || meta.Size_ < 0 || meta.Size_ > limits.MaxVariantBytes || meta.Size_ > limits.MaxTotalBytes-total ||
			(meta.Path != "" && meta.Path != entry.path) {
			return nil, ErrNativeFileCapture
		}
		plain, err := nativeLocalReader(ctx, dag, contentLink.Cid, key)
		if err != nil {
			return nil, err
		}
		path := filepath.Join(privateDirectory, nativeFileHash([]byte(captured.FileId+"\x00"+entry.path))+".payload")
		out, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			plain.Close()
			return nil, err
		}
		created = append(created, path)
		hash0, hash1 := sha256.New(), sha256.New()
		n, readErr := io.CopyBuffer(io.MultiWriter(out, hash0, hash1),
			io.LimitReader(nativeContextReader{ctx, plain}, limits.MaxVariantBytes+1), make([]byte, 256<<10))
		readErr = errors.Join(readErr, plain.Close(), out.Sync(), out.Close())
		if readErr != nil || n != meta.Size_ || n > limits.MaxVariantBytes {
			return nil, errors.Join(ErrNativeFileCapture, readErr)
		}
		total += n
		if total > limits.MaxTotalBytes {
			return nil, ErrNativeFileCapture
		}
		plainSHA := hex.EncodeToString(hash0.Sum(nil))
		_, _ = hash0.Write([]byte{0})
		_, _ = hash1.Write([]byte{1})
		check0, check1 := base32.RawHexEncoding.EncodeToString(hash0.Sum(nil)), base32.RawHexEncoding.EncodeToString(hash1.Sum(nil))
		verified := meta.Checksum != "" && (meta.Checksum == check0 || (key == "" && meta.Checksum == check1))
		if meta.Checksum != "" && !verified {
			return nil, ErrNativeFileCapture
		}
		if err := os.Chmod(path, 0400); err != nil {
			return nil, err
		}
		st, err := os.Lstat(path)
		if err != nil {
			return nil, err
		}
		capture.variants = append(capture.variants, NativeFileVariant{
			path: entry.path, contentID: contentLink.Cid.String(), metadataID: metaLink.Cid.String(),
			name: meta.Name, mime: meta.Media, checksum: meta.Checksum, source: meta.Source, plainSHA: plainSHA,
			localPath: path, bytes: n, original: entry.path == "/0/" || entry.path == filemodels.OriginalImagePath,
			nativeChecksumVerified: verified, fileInfo: st, metadata: append([]byte(nil), raw...),
		})
	}
	if len(usedKeys) != len(keys) {
		return nil, ErrNativeFileCapture
	}
	originals := 0
	for _, variant := range capture.variants {
		if variant.original {
			originals++
		}
	}
	if originals != 1 {
		return nil, ErrNativeFileCapture
	}
	sort.Strings(dagRows)
	capture.dagSHA = nativeFileHash([]byte(strings.Join(dagRows, "\n")))
	capture.complete = true
	success = true
	return capture, nil
}
