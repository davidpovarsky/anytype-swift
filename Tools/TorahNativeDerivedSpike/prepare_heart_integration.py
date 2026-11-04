"""Generate a reviewable exact patch. NEVER applies or writes to Heart."""
from pathlib import Path
import argparse, difflib, hashlib, json, subprocess

PIN = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
product = root / 'Modules/PinkhaHeart'
assert subprocess.check_output(['git','-C',str(args.heart_source),'rev-parse','HEAD'], text=True).strip() == PIN
changes = {}
def edit(path, old, new):
    if path not in changes:
        original = subprocess.check_output(['git','-C',str(args.heart_source),'show',f'{PIN}:{path}']).decode('utf8')
        changes[path] = [original, original]
    assert changes[path][1].count(old) == 1, (path, old)
    changes[path][1] = changes[path][1].replace(old,new)
def add(path, content):
    changes[path] = ['', content]

for source in sorted((product/'torah').glob('*.go')):
    add('core/pinkha/torah/'+source.name,source.read_text(encoding='utf8'))
for source in sorted((product/'engine').glob('*.go')):
    add('core/pinkha/torahindex/'+source.name,source.read_text(encoding='utf8').replace(
        'github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah',
        'github.com/anyproto/anytype-heart/core/pinkha/torah'))
for source in sorted((product/'values').glob('*.go')):
    if source.name.endswith('_test.go'): continue
    add('core/pinkha/torahvalues/'+source.name,source.read_text(encoding='utf8').replace(
        'github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah',
        'github.com/anyproto/anytype-heart/core/pinkha/torah'))
for source in sorted((product/'transport').glob('*.go')):
    if source.name.endswith('_test.go'): continue
    add('core/pinkha/torahtransport/'+source.name,source.read_text(encoding='utf8').replace(
        'github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah',
        'github.com/anyproto/anytype-heart/core/pinkha/torah'))

# Use the original importer's complete identity map after allocation and before
# any schema/document object is created. Projection never rewrites user data.
processor='core/block/import/processor.go'
edit(processor,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torahtransport "github.com/anyproto/anytype-heart/core/pinkha/torahtransport"')
edit(processor,'\tdataObject := creator.NewDataObject(',''' objects:=make([]torahtransport.Object,0,len(p.converterResponse.Snapshots))
 for _,snapshot:=range p.converterResponse.Snapshots {
  if snapshot.Snapshot!=nil && snapshot.Snapshot.Data!=nil {
   data:=snapshot.Snapshot.Data
   objects=append(objects,torahtransport.Object{ID:snapshot.Id,OriginalID:data.Details.GetString(bundle.RelationKeyOldAnytypeID),PropertyKey:data.Key,Details:data.Details})
  }
 }
 if err:=torahtransport.RemapObjects(p.request.SpaceId,objects,p.oldIDToNew);err!=nil {
  p.errors.Add(err)
  return nil,""
 }
\tdataObject := creator.NewDataObject(''')

add('pkg/lib/bundle/pinkha_torah.go','''package bundle

import (
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 "github.com/anyproto/anytype-heart/pkg/lib/localstore/addr"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Package variables precede init(): the native local/derived key lists include
// these immutable list properties. No option objects or global installed rows.
var pinkhaTorahRegistered = func() bool {
 for _,d:=range torah.Definitions {
  key:=domain.RelationKey(d.Key)
  relations[key]=&model.Relation{Id:addr.BundledRelationURLPrefix+d.Key,
   Key:d.Key,Name:d.Name,Format:model.RelationFormat_tag,
   DataSource:model.Relation_derived,ReadOnly:true,ReadOnlyRelation:true,
   Scope:model.Relation_type,MaxCount:0}
 }
 // Private capability/label/readiness fields use the same native exclusion
 // rules as derived properties for CRDT snapshots, export and local injection.
 for _,key:=range torah.LocalKeys()[3:] {
  format:=model.RelationFormat_longtext
  if key==torah.ReadyKey{format=model.RelationFormat_checkbox}
  if key==torah.VersionKey{format=model.RelationFormat_number}
  relations[domain.RelationKey(key)]=&model.Relation{Id:addr.BundledRelationURLPrefix+key,
   Key:key,Name:key,Format:format,Hidden:true,
   DataSource:model.Relation_derived,ReadOnly:true,ReadOnlyRelation:true,Scope:model.Relation_type}
 }
 return true
}()
''')

store='pkg/lib/localstore/objectstore/spaceindex/store.go'
edit(store,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torahindex "github.com/anyproto/anytype-heart/core/pinkha/torahindex"')
edit(store,'type dsObjectStore struct {','type dsObjectStore struct {\n torahInitMu sync.Mutex\n torah *torahindex.Index\n torahOutbox anystore.Collection\n torahFT *torahFulltextWorker')
edit(store,'func (s *dsObjectStore) Close() error {','func (s *dsObjectStore) Close() error {\n s.stopTorahFulltext()')
edit(store,'func (s *dsObjectStore) Init() error {','func (s *dsObjectStore) initBase() error {')
add('pkg/lib/localstore/objectstore/spaceindex/pinkha_torah.go','''package spaceindex

import (
 "context"
 "github.com/anyproto/anytype-heart/core/domain"
 torahindex "github.com/anyproto/anytype-heart/core/pinkha/torahindex"
)

func (s *dsObjectStore) Init() error {
 if err:=s.initBase();err!=nil{return err}
 s.torahInitMu.Lock()
 defer s.torahInitMu.Unlock()
 if s.torah!=nil{return nil}
 var err error
 s.torahOutbox,err=s.db.Collection(s.componentCtx,"_pinkhaTorahFulltextOutbox")
 if err!=nil{return err}
 index:=torahindex.New(s.spaceId,s.objects,s.WriteTx,s.updateObjectDetails,s.db.ReadTx).WithChangeHook(s.recordTorahFulltext)
 // initBase has released s.lock; post-commit notification delivery takes it.
 if err:=index.Recover(s.componentCtx);err!=nil{return err}
 s.torah=index
 s.prepareTorahFulltext()
 s.startTorahFulltext()
 return nil
}

func (s *dsObjectStore) nativeTorah()*torahindex.Index {
 s.torahInitMu.Lock();defer s.torahInitMu.Unlock()
 return s.torah
}

func (s *dsObjectStore) TorahLocalDetails(ctx context.Context, details *domain.Details) (*domain.Details, error) {
 if index:=s.nativeTorah();index!=nil{return index.LocalDetails(ctx,details)}
 return nil,nil
}
''')
add('pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_fulltext.go','''package spaceindex

import (
 "context"
 "errors"
 "strings"
 "time"
 anystore "github.com/anyproto/any-store"
 "github.com/anyproto/any-store/anyenc"
 "github.com/anyproto/any-store/query"
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 values "github.com/anyproto/anytype-heart/core/pinkha/torahvalues"
)

type torahFulltextWorker struct {
 ctx context.Context
 cancel context.CancelFunc
 wake chan struct{}
 done chan struct{}
}

func(s *dsObjectStore)prepareTorahFulltext(){
 ctx,cancel:=context.WithCancel(s.componentCtx)
 s.torahFT=&torahFulltextWorker{ctx:ctx,cancel:cancel,wake:make(chan struct{},1),done:make(chan struct{})}
}

func(s *dsObjectStore)startTorahFulltext(){
 worker:=s.torahFT
 go func(){
  defer close(worker.done)
  for {
   retry:=s.drainTorahFulltext(worker.ctx)
   var timer *time.Timer
   var retryAt <-chan time.Time
   if retry {timer=time.NewTimer(5*time.Second);retryAt=timer.C}
   select {case <-worker.ctx.Done():if timer!=nil{timer.Stop()};return
    case <-worker.wake:case <-retryAt:}
   if timer!=nil{timer.Stop()}
  }
 }()
}

func(s *dsObjectStore)scheduleTorahFulltext(){
 if worker:=s.torahFT;worker!=nil{select{case worker.wake<-struct{}{}:default:}}
}

func(s *dsObjectStore)stopTorahFulltext(){
 if worker:=s.torahFT;worker!=nil{worker.cancel();<-worker.done}
}

// The outbox is in the SAME per-Space DB/transaction as canonical projection.
// It contains only document IDs and a retry token, never association payloads.
func (s *dsObjectStore) recordTorahFulltext(ctx context.Context,id string,before,after *domain.Details) error {
 native:=func(d *domain.Details)bool{return d!=nil&&d.GetString(domain.RelationKey(torah.CanonicalKeyKey))!=""}
 if !native(before)&&!native(after){return nil}
 token:=values.SearchFingerprint(after)
 if values.SearchFingerprint(before)==token{return nil}
 _,err:=s.torahOutbox.UpsertId(ctx,id,query.ModifyFunc(func(a *anyenc.Arena,_ *anyenc.Value)(*anyenc.Value,bool,error){
  value:=a.NewObject();value.Set("id",a.NewString(id));value.Set("token",a.NewString(token));return value,true,nil
 }))
 if err!=nil{return err}
 if buffer,ok:=ctx.Value(txNotificationsKey{}).(*txNotifications);ok&&buffer!=nil{
  buffer.mu.Lock();buffer.torahFulltext=true;buffer.mu.Unlock()
 }
 return nil
}

// Enqueue only AFTER the root transaction commits. Remove an outbox entry only
// after the native common-DB queue commits, and only if its token still matches.
// A crash at either boundary causes a harmless retry on the next Space open.
func (s *dsObjectStore) drainTorahFulltext(ctx context.Context) bool {
 if s.torahOutbox==nil||s.fulltextQueue==nil{return false}
 iter,err:=s.torahOutbox.Find(nil).Iter(ctx)
 if err!=nil{log.Warnf("Torah FT outbox read: %v",err);return true}
 type entry struct{id,token string}
 var pending []entry
 for iter.Next(){doc,e:=iter.Doc();if e!=nil{err=e;break};pending=append(pending,entry{strings.Clone(doc.Value().GetString("id")),strings.Clone(doc.Value().GetString("token"))})}
 if err==nil{err=iter.Err()};iter.Close()
 if err!=nil{log.Warnf("Torah FT outbox iterate: %v",err);return true}
 for start:=0;start<len(pending);start+=256{
  end:=min(start+256,len(pending));batch:=pending[start:end]
  ids:=make([]domain.FullID,0,len(batch));for _,item:=range batch{ids=append(ids,domain.FullID{SpaceID:s.spaceId,ObjectID:item.id})}
  if _,_,err=s.fulltextQueue.AddToIndexQueue(ctx,ids...);err!=nil{log.Warnf("Torah native FT enqueue: %v",err);return true}
  tx,e:=s.db.WriteTx(ctx);if e!=nil{log.Warnf("Torah FT outbox transaction: %v",e);return true}
  for _,item:=range batch{
   doc,e:=s.torahOutbox.FindId(tx.Context(),item.id)
   if errors.Is(e,anystore.ErrDocNotFound){continue}
   if e!=nil{err=e;break}
   if doc.Value().GetString("token")==item.token{if e=s.torahOutbox.DeleteId(tx.Context(),item.id);e!=nil{err=e;break}}
  }
  if err==nil{err=tx.Commit()};tx.Rollback()
  if err!=nil{log.Warnf("Torah FT outbox acknowledge: %v",err);return true}
 }
 return false
}
''')
add('pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_fulltext_test.go',
    (root/'Tools/PinkhaNativeDerived/native_test_templates/pinkha_torah_fulltext_test.go').read_text(encoding='utf8'))
update='pkg/lib/localstore/objectstore/spaceindex/update.go'
edit(update,'\tmu      sync.Mutex\n\tpending []string','\tmu      sync.Mutex\n torahFulltext bool\n\tpending []string')
edit(update,'\tpending := buf.pending\n','\tpending := buf.pending\n torahFulltext:=buf.torahFulltext\n buf.torahFulltext=false\n')
edit(update,'\tbuf.mu.Unlock()\n\n\tfor _, id := range pending {','\tbuf.mu.Unlock()\n if torahFulltext {defer s.scheduleTorahFulltext()}\n\n\tfor _, id := range pending {')
edit(update,'func (s *dsObjectStore) UpdateObjectDetails(ctx context.Context, id string, details *domain.Details) error {','''func (s *dsObjectStore) UpdateObjectDetails(ctx context.Context, id string, details *domain.Details) error {
 if index:=s.nativeTorah();index!=nil{return index.Update(ctx,id,details)}
 return s.updateObjectDetails(ctx,id,details)
}

func (s *dsObjectStore) updateObjectDetails(ctx context.Context, id string, details *domain.Details) error {''')
edit(update,'func (s *dsObjectStore) ModifyObjectDetailsCtx(ctx context.Context, id string, proc func(details *domain.Details) (*domain.Details, bool, error), upsert bool) error {','''func (s *dsObjectStore) ModifyObjectDetailsCtx(ctx context.Context, id string, proc func(details *domain.Details) (*domain.Details, bool, error), upsert bool) error {
 if index:=s.nativeTorah();index!=nil{return index.Modify(ctx,id,proc,upsert,s.modifyObjectDetailsCtx)}
 return s.modifyObjectDetailsCtx(ctx,id,proc,upsert)
}

func (s *dsObjectStore) modifyObjectDetailsCtx(ctx context.Context, id string, proc func(details *domain.Details) (*domain.Details, bool, error), upsert bool) error {''')
delete='pkg/lib/localstore/objectstore/spaceindex/delete.go'
edit(delete,'func (s *dsObjectStore) DeleteDetails(ctx context.Context, ids []string) error {','''func (s *dsObjectStore) DeleteDetails(ctx context.Context, ids []string) error {
 if index:=s.nativeTorah();index!=nil{return index.Delete(ctx,ids,func(ctx context.Context)error{return s.deleteDetails(ctx,ids)})}
 return s.deleteDetails(ctx,ids)
}

func (s *dsObjectStore) deleteDetails(ctx context.Context, ids []string) error {''')
filter='pkg/lib/database/filter.go'
edit(filter,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
edit(filter,'func makeFilter(spaceID string, rawFilter FilterRequest, store ObjectStore) (Filter, error) {','''func makeFilter(spaceID string, rawFilter FilterRequest, store ObjectStore) (Filter, error) {
 filter,err:=makeNativeFilter(spaceID,rawFilter,store)
 if err!=nil||filter==nil||!torah.IsProperty(string(rawFilter.RelationKey)){return filter,err}
 // Negative/empty predicates must not match malformed, ineligible or stale
 // documents. Rebuilds change every row atomically at the native boundary.
 return FiltersAnd{FilterIn{Key:domain.RelationKey(torah.ReadyKey),Value:[]domain.Value{domain.Bool(true)}},filter},nil
}

func makeNativeFilter(spaceID string, rawFilter FilterRequest, store ObjectStore) (Filter, error) {''')

# The original option API accepts any relation key. Canonical derived values
# must never gain a second option-Object store, including on older clients.
options='core/block/object/objectcreator/relation_option.go'
edit(options,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
edit(options,'\tif !details.Has(bundle.RelationKeyCreatedDate) {',''' if torah.IsProperty(details.GetString(bundle.RelationKeyRelationKey)) {
  return "", nil, fmt.Errorf("canonical derived properties do not have option Objects")
 }
\tif !details.Has(bundle.RelationKeyCreatedDate) {''')

# Keep the original editor's live state and emitted Details events consistent
# with the same canonical projection used by the native query index.
inject='core/block/editor/smartblock/detailsinject.go'
edit(inject,'\tsb.updateBackLinks(s)\n','\tsb.updateBackLinks(s)\n sb.injectTorahDetails(s)\n')
add('core/block/editor/smartblock/pinkha_torah.go','''package smartblock

import (
 "context"
 "github.com/anyproto/anytype-heart/core/block/editor/state"
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
)

func (sb *smartBlock) injectTorahDetails(s *state.State) {
 projector,ok:=sb.spaceIndex.(interface{
  TorahLocalDetails(context.Context,*domain.Details)(*domain.Details,error)
 })
 if !ok{return}
 details,err:=projector.TorahLocalDetails(context.Background(),s.CombinedDetails())
 if err!=nil {
  log.Warnf("Torah local projection unavailable: %v",err)
  details=domain.NewDetails()
 }
 if details==nil{return}
 for _,key:=range torah.LocalKeys(){s.RemoveLocalDetail(domain.RelationKey(key))}
 s.AddLocalDetails(details)
}
''')
details='core/block/editor/basic/details.go'
edit(details,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
edit(details,'\tfor key, value := range diff.Iterate() {',''' for _,key:=range removedKeys {
  if torah.IsLocalKey(string(key)){return fmt.Errorf("canonical derived property cannot be removed directly: %w",domain.ErrValidationFailed)}
 }
\tfor key, value := range diff.Iterate() {
  if torah.IsLocalKey(string(key)){return fmt.Errorf("canonical derived property cannot be written directly: %w",domain.ErrValidationFailed)}''')

# Native exports omit local caches; canonical longText and unknown fields remain
# byte-for-byte intact. Each converter also has direct callers outside export.
for path in ['core/converter/pbc/pbc.go','core/converter/pbjson/pbjson.go','core/block/export/anyblock/anyblock.go']:
    edit(path,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torahvalues "github.com/anyproto/anytype-heart/core/pinkha/torahvalues"')
    edit(path,'Details:     st.CombinedDetails().ToProto(),','Details:     torahvalues.ExportDetails(st.CombinedDetails()).ToProto(),')

# Canonical identity strings are values, not graph or option-Object IDs.
links='core/block/object/objectlink/dependent_objects.go'
edit(links,'"github.com/anyproto/anytype-heart/core/domain"','"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
edit(links,'func collectIdsFromDetail(rel *model.RelationLink, det *domain.Details, flags Flags) (ids []string) {','''func collectIdsFromDetail(rel *model.RelationLink, det *domain.Details, flags Flags) (ids []string) {
 if torah.IsProperty(rel.Key){return nil}''')
dataview='core/block/simple/dataview/dataview.go'
edit(dataview,'"github.com/anyproto/anytype-heart/pb"','"github.com/anyproto/anytype-heart/pb"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
edit(dataview,'\tfor _, filter := range filters {','\tfor _, filter := range filters {\n if torah.IsProperty(filter.RelationKey){continue}')

fulltext='core/indexer/fulltext.go'
edit(fulltext,'i.prepareRelationSearchDocs(object.FullId(), sb)','i.prepareRelationSearchDocs(object.FullId(), sb, details)')
edit(fulltext,'func (i *indexer) prepareRelationSearchDocs(fullId domain.FullID, sb smartblock.SmartBlock) (docs []ftsearch.SearchDoc) {','''func (i *indexer) prepareRelationSearchDocs(fullId domain.FullID, sb smartblock.SmartBlock, indexed ...*domain.Details) (docs []ftsearch.SearchDoc) {
 var native *domain.Details
 if len(indexed)>0{native=indexed[0]}''')
edit(fulltext,'docs = i.prepareRelationSearchDocsFromDetails(fullId, layout, sb.Details())','''docs = i.prepareRelationSearchDocsFromDetails(fullId, layout, i.withoutTorahCanonicalText(sb.Details(),native))
 docs = append(docs,i.prepareTorahSearchDocs(fullId,native)...)''')
add('core/indexer/pinkha_torah.go','''package indexer

import (
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 values "github.com/anyproto/anytype-heart/core/pinkha/torahvalues"
 "github.com/anyproto/anytype-heart/pkg/lib/localstore/ftsearch"
)

func (i *indexer) withoutTorahCanonicalText(details,indexed *domain.Details)*domain.Details{
 if indexed==nil{return details}
 key:=indexed.GetString(domain.RelationKey(torah.CanonicalKeyKey))
 if key==""{return details}
 return details.CopyWithoutKeys(domain.RelationKey(key))
}

func (i *indexer) prepareTorahSearchDocs(id domain.FullID,details *domain.Details)(docs []ftsearch.SearchDoc){
 if details==nil{return nil}
 texts:=values.SearchTexts(details)
 for _,definition:=range torah.Definitions{
  text:=texts[definition.Key]
  if text!=""{docs=append(docs,ftsearch.SearchDoc{Id:domain.NewObjectPathWithRelation(id.ObjectID,definition.Key).String(),SpaceId:id.SpaceID,Text:text})}
 }
 return docs
}
''')

args.output.mkdir(parents=True,exist_ok=True)
patch=''
inventory=[]
for path,(before,after) in sorted(changes.items()):
    after=after.replace('\r\n','\n')
    patch+='diff --git a/'+path+' b/'+path+'\n'
    if not before: patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path if before else '/dev/null',tofile='b/'+path))
    inventory.append(dict(path=path,before_sha256=hashlib.sha256(before.encode()).hexdigest() if before else None,after_sha256=hashlib.sha256(after.encode()).hexdigest()))
patch_bytes=patch.encode('utf8')
(args.output/'native-heart-integration.patch').write_bytes(patch_bytes)
(args.output/'native-heart-integration.json').write_text(json.dumps(dict(heart_sha=PIN,patch_sha256=hashlib.sha256(patch_bytes).hexdigest(),status='REVIEW_ARTIFACT_NOT_APPLIED',files=inventory),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(patch=str(args.output/'native-heart-integration.patch'),sha256=hashlib.sha256(patch_bytes).hexdigest(),files=len(inventory))))
