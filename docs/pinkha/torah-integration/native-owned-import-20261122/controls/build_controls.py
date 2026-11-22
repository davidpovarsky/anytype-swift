"""Build an explicit unit closure of new owned channel/provider/drain boundaries.

The original component ABI below is a declared fixture. No account, native
storage, network upload or applied-body result is simulated as acceptance.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'controls/module'
fragments = []
products = []
if MODULE.exists():
    # This directory contains only the explicitly generated fixture closure.
    shutil.rmtree(MODULE)

def write(path, text):
    destination = MODULE / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(text.encode())

def actual(source, destination):
    raw = source.read_bytes()
    path = MODULE / destination
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    products.append(dict(source=str(source.relative_to(ROOT.parent)), compiled_path=destination,
        bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), full_file=True,
        kind='control' if source.parent == ROOT/'controls' else 'original' if 'original' in source.parts else 'candidate'))

def fragment(source, start, end):
    raw = source.read_bytes().decode()
    assert raw.count(start) == 1
    selected = raw[raw.index(start):]
    selected = selected[:selected.index(end)] if end else selected
    fragments.append(dict(source=str(source.relative_to(ROOT.parent)), start=start, end=end,
        source_sha256=hashlib.sha256(raw.encode()).hexdigest(), fragment_sha256=hashlib.sha256(selected.encode()).hexdigest(), bytes=len(selected.encode())))
    return selected

write('go.mod', '''module github.com/anyproto/anytype-heart
go 1.25.0
require github.com/anyproto/any-sync v0.0.0
require go.uber.org/zap v0.0.0
replace github.com/anyproto/any-sync => ./fixture-modules/any-sync
replace go.uber.org/zap => ./fixture-modules/zap
''')
write('fixture-modules/any-sync/go.mod', 'module github.com/anyproto/any-sync\ngo 1.25.0\n')
write('fixture-modules/any-sync/commonspace/object/tree/treestorage/fixture.go', 'package treestorage\ntype TreeStorageCreatePayload struct{}\n')
write('fixture-modules/zap/go.mod', 'module go.uber.org/zap\ngo 1.25.0\n')
write('fixture-modules/zap/fixture.go', 'package zap\nfunc Error(err error) any { return err }\n')
write('core/domain/fixture.go', '''package domain
import "iter"
type RelationKey string
type FileId string
type FullID struct { SpaceID, ObjectID string }
type FullFileId struct { SpaceId string; FileId FileId }
type FileEncryptionKeys struct { FileId FileId; EncryptionKeys map[string]string }
type Details struct { Values map[RelationKey]string }
func NewDetails() *Details { return &Details{Values:map[RelationKey]string{}} }
func (d *Details) GetString(k RelationKey) string { if d==nil{return ""}; return d.Values[k] }
func (d *Details) Set(k RelationKey,v string) { d.Values[k]=v }
func (d *Details) Iterate() iter.Seq2[RelationKey,string] { return func(yield func(RelationKey,string) bool) {for k,v:=range d.Values {if !yield(k,v){return}}} }
func (d *Details) ToProto() any {return d}
''')
write('core/domain/objectorigin/fixture.go', 'package objectorigin\ntype ObjectOrigin struct{}\n')
write('pkg/lib/pb/model/fixture.go', '''package model
type BlockContentFileType int32
type BlockContentFileState int32
const BlockContentFile_Uploading BlockContentFileState=1
type ImportType int32
func (i ImportType) String() string { return "fixture_pb" }
type Bookmark struct { TargetObjectId, Url string }
type Text struct { IconImage string }
func (t *Text) GetIconImage() string {return t.IconImage}
type Block struct { Bookmark *Bookmark; File any; Text *Text }
func (b *Block) GetBookmark() *Bookmark {return b.Bookmark}
func (b *Block) GetFile() any {return b.File}
func (b *Block) GetText() *Text {return b.Text}
''')
write('core/block/simple/fixture.go', '''package simple
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type Block interface { Model() *model.Block }
''')
write('core/block/simple/file/fixture.go', '''package file
import "github.com/anyproto/anytype-heart/core/block/simple"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type Block interface { simple.Block; SetState(model.BlockContentFileState); Copy() simple.Block }
''')
write('core/block/editor/smartblock/fixture.go', 'package smartblock\ntype SmartBlock interface{}\n')
write('core/block/cache/fixture.go', '''package cache
import "context"
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
type ObjectGetter interface {
 GetObject(context.Context,string)(smartblock.SmartBlock,error)
 GetObjectByFullID(context.Context,domain.FullID)(smartblock.SmartBlock,error)
}
''')
write('core/session/fixture.go', 'package session\ntype Context interface{}\n')
write('pb/fixture.go', '''package pb
type RpcFileUploadRequest struct { SpaceId,Url,LocalPath string; Details any }
''')
write('core/block/fixture.go', '''package block
import "context"
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/domain/objectorigin"
import "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
import "github.com/anyproto/anytype-heart/core/files/fileuploader"
import "github.com/anyproto/anytype-heart/core/session"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
import "github.com/anyproto/anytype-heart/pb"
type FileUploadRequest struct { pb.RpcFileUploadRequest; ObjectOrigin objectorigin.ObjectOrigin; CustomEncryptionKeys map[string]string; CreatedInContext string; PreloadOnly bool }
type UploadRequest struct {ContextId, BlockId string}
type Service struct {
 Upload func(context.Context,string,FileUploadRequest)(string,model.BlockContentFileType,*domain.Details,error)
 Start func(context.Context,session.Context,UploadRequest,string)(*fileuploader.OwnedUpload,error)
 Get func(context.Context,string)(smartblock.SmartBlock,error)
 GetFull func(context.Context,domain.FullID)(smartblock.SmartBlock,error)
}
func (s *Service) UploadFile(c context.Context, id string, r FileUploadRequest)(string,model.BlockContentFileType,*domain.Details,error){return s.Upload(c,id,r)}
func (s *Service) StartOwnedBlockFile(c context.Context,e session.Context,r UploadRequest,g string)(*fileuploader.OwnedUpload,error){return s.Start(c,e,r,g)}
func (s *Service) GetObject(c context.Context,id string)(smartblock.SmartBlock,error){return s.Get(c,id)}
func (s *Service) GetObjectByFullID(c context.Context,id domain.FullID)(smartblock.SmartBlock,error){return s.GetFull(c,id)}
''')
actual(ROOT / 'candidate/native/core/files/fileuploader/owned_upload.go', 'core/files/fileuploader/owned_upload.go')
uploader = ROOT / 'candidate/native/core/files/fileuploader/uploader.go'
upload_result = fragment(uploader, 'type UploadResult struct {', '\nfunc (ur UploadResult) ToBlock')
upload_async = fragment(uploader, 'func (u *uploader) UploadAsync(', '\nfunc (u *uploader) addFile(')
write('core/files/fileuploader/actual_async_and_fixture.go', '''package fileuploader
import "context"
import "github.com/anyproto/anytype-heart/core/block/cache"
import "github.com/anyproto/anytype-heart/core/block/simple/file"
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
// Explicit ABI/callback fixture: no real filesystem, storage or native upload.
type Uploader interface {UploadAsync(context.Context) chan UploadResult}
type uploader struct {serviceCtx context.Context; preloadId string; picker cache.ObjectGetter; block file.Block; upload func(context.Context) UploadResult}
func (u *uploader) Upload(c context.Context) UploadResult {return u.upload(c)}
func FixturePrepared(c context.Context,g cache.ObjectGetter, f func(context.Context) UploadResult) Uploader {return &uploader{serviceCtx:c,picker:g,upload:f}}
type logger struct{}
func (logger) Errorf(string,...any){}
var log logger
'''+upload_result+'\n'+upload_async)

write('pkg/lib/core/smartblock/fixture.go', '''package smartblock
type SmartBlockType int32
const (
 SmartBlockTypeWorkspace SmartBlockType=iota
 SmartBlockTypeWidget
 SmartBlockTypeRelation
 SmartBlockTypeObjectType
 SmartBlockTypeRelationOption
 SmartBlockTypePage
 SmartBlockTypeFileObject
 SmartBlockTypeFile
 SmartBlockTypeProfilePage
 SmartBlockTypeTemplate
 SmartBlockTypeParticipant
 SmartBlockTypeChatDerivedObject
)
''')
write('core/block/import/common/fixture.go', '''package common
import "errors"
import "github.com/anyproto/anytype-heart/core/domain"
import sb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
var ErrCancel=errors.New("fixture import cancellation")
var ErrFileLoad=errors.New("fixture original file load category")
type Key struct {Path,Key string}
type FileInfo struct {FileId string; EncryptionKeys []Key}
type Data struct {Details *domain.Details; FileInfo *FileInfo}
type FileKeys struct {Hash string; Keys map[string]string}
type NativeSnapshot struct {SbType sb.SmartBlockType; Data *Data; FileKeys []FileKeys}
type Snapshot struct {Id string; Snapshot *NativeSnapshot}
type ConvertError struct {All []error}
func (e *ConvertError) Add(err error) {e.All=append(e.All,err)}
func (e *ConvertError) Error() error {return errors.Join(e.All...)}
''')
actual(ROOT.parent / 'native-map-audit/original/core/block/import/common/workerpool/workerpool.go', 'core/block/import/common/workerpool/workerpool.go')
actual(ROOT.parent / 'native-map-audit/original/core/block/import/common/objectcreator/task.go', 'core/block/import/common/objectcreator/task.go')
write('core/block/import/common/objectcreator/fixture.go', '''package objectcreator
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/block/import/common"
type Service interface {Create(*DataObject,*common.Snapshot)(*domain.Details,string,error)}
type FixtureService func(*DataObject,*common.Snapshot)(*domain.Details,string,error)
func (s FixtureService) Create(d *DataObject,n *common.Snapshot)(*domain.Details,string,error){return s(d,n)}
''')
write('pkg/lib/bundle/fixture.go', '''package bundle
import "github.com/anyproto/anytype-heart/core/domain"
const RelationKeySource domain.RelationKey="source"
const RelationKeyId domain.RelationKey="id"
const RelationKeyIconImage domain.RelationKey="iconImage"
''')
write('pkg/lib/logging/fixture.go', '''package logging
type Logger struct{}
func LoggerNotSugared(string) Logger{return Logger{}}
func (Logger) Error(string,...any){}
''')
write('space/fixture.go', 'package space\ntype Service interface{}\n')
write('pkg/lib/localstore/objectstore/fixture.go', '''package objectstore
import "github.com/anyproto/anytype-heart/core/domain"
type ObjectStore interface {AddFileKeys(domain.FileEncryptionKeys) error}
''')
write('core/files/fileobject/fixture.go', '''package fileobject
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/domain/objectorigin"
type Service interface {CreateFromImport(domain.FullFileId,objectorigin.ObjectOrigin,*domain.Details)(string,error)}
''')
for name in ['provider.go', 'fileobject.go', 'oldfile.go', 'file_upload_provider.go']:
    actual(ROOT / ('provider-admission/candidate/native/core/block/import/common/objectid/' + name), 'core/block/import/common/objectid/' + name)
write('core/block/import/common/objectid/fixture.go', '''package objectid
import "context"
import "time"
import "github.com/anyproto/any-sync/commonspace/object/tree/treestorage"
import "github.com/anyproto/anytype-heart/core/block"
import "github.com/anyproto/anytype-heart/core/block/import/common"
import "github.com/anyproto/anytype-heart/core/domain/objectorigin"
import "github.com/anyproto/anytype-heart/core/files/fileobject"
import "github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore"
import "github.com/anyproto/anytype-heart/space"
type treeObject struct{}
func (*treeObject) GetIDAndPayload(context.Context,string,*common.Snapshot,time.Time,bool,objectorigin.ObjectOrigin)(string,treestorage.TreeStorageCreatePayload,error){return "fixture-tree-id",treestorage.TreeStorageCreatePayload{},nil}
func newExistingObject(objectstore.ObjectStore) *treeObject{return &treeObject{}}
func newTreeObject(*treeObject,space.Service) *treeObject{return &treeObject{}}
func newDerivedObject(*treeObject,space.Service,objectstore.ObjectStore) *treeObject{return &treeObject{}}
func newWorkspace(space.Service) *treeObject{return &treeObject{}}
func newWidget(space.Service) *treeObject{return &treeObject{}}
func newParticipant() *treeObject{return &treeObject{}}
// Exact ordinary constructor ABI remains callable from original consumers.
var _ func(objectstore.ObjectStore,space.Service,*block.Service,fileobject.Service) IdAndKeyProvider = NewIDProvider
''')
for name in ['owned_import_files.go', 'owned_import_drain.go', 'owned_import_finalize.go']:
    actual(ROOT / ('import-layer/candidate/native/core/block/import/' + name), 'core/block/import/' + name)
add_work = fragment(ROOT / 'import-layer/candidate/native/core/block/import/processor.go', 'func (p *importProcessor) addWork(', '\nfunc (p *importProcessor) readResults(')
write('metrics/fixture.go', 'package metrics\ntype ImportFinishedEvent struct{ID,ImportType string}\n')
write('core/block/import/fixture.go', '''package importer
import "context"
import "github.com/anyproto/anytype-heart/core/block/import/common"
import creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
import "github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type progressFixture struct{}
func (progressFixture) TryStep(int)error{return nil}
type requestFixture struct {Progress progressFixture; Type model.ImportType}
type responseFixture struct {Err error}
type dependencyFixture struct {objectCreator creator.Service}
const workerPoolSize=32
type importProcessor struct {
 owned *ownedImportExecution
 errors *common.ConvertError
 deps *dependencyFixture
 request *requestFixture
 response *responseFixture
 nativeMapping *struct{}
 nativeMappingBatchesDrained int
 widgetCalls,finishCalls,eventCalls int
}
func (p *importProcessor) addRootCollectionWidget(context.Context){p.widgetCalls++}
func (p *importProcessor) finishImportProcess(){p.finishCalls++}
func (p *importProcessor) sendImportFinishEvent(){p.eventCalls++}
func recordEvent(any){}
'''+add_work)
for relative in ['core/files/fileuploader/owned_upload_test.go', 'core/block/import/owned_import_test.go']:
    actual(ROOT / 'controls' / Path(relative).name, relative)

expected_tests = []
for relative in ['core/files/fileuploader/owned_upload_test.go', 'core/block/import/owned_import_test.go']:
    names = re.findall(r'^func (Test\w+)\(', (MODULE/relative).read_text(), re.M)
    assert len(names) == len(set(names))
    expected_tests.extend(dict(package='github.com/anyproto/anytype-heart/'+str(Path(relative).parent).replace('\\','/'), name=name) for name in names)

files, payload = [], []
for path in sorted(MODULE.rglob('*')):
    if path.is_file():
        raw=path.read_bytes();row=dict(path=path.relative_to(MODULE).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        files.append(row);payload.append(dict(**row,gzip_b64=base64.b64encode(gzip.compress(raw,mtime=0)).decode()))
source=dict(scope='New owned uploader/importer/provider unit boundaries over exact actual source files/fragments and original WorkerPool/task. Explicit component ABI/callback fixtures; no full original native module, account, storage, real file upload, body success or ACK.',
    full_actual_source_files=products, actual_source_fragments=fragments, module_files=files,
    fixture_scope='All files named fixture.go, actual_async_and_fixture.go declarations/Upload callback and separate any-sync/zap replacement modules are explicit dependency fixtures. Full newOwnedImportDependencies, original block/editor hooks and complete importer.Execute are not compiled by this unit closure.',
    expected_tests=expected_tests, prior_controls_replayed=0, native_executions=0)
(ROOT/'controls/SOURCE.json').write_text(json.dumps(source,indent=2)+'\n')
(ROOT/'controls/INPUT_PACKET.json').write_text(json.dumps(dict(files=payload,source_manifest=source),separators=(',',':')))
print(json.dumps(dict(module_files=len(files),full_source_files=len(products),actual_fragments=len(fragments),scope=source['scope'])))
