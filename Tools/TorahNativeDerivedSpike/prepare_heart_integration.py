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
edit(store,'type dsObjectStore struct {','type dsObjectStore struct {\n torahInitMu sync.Mutex\n torah *torahindex.Index')
edit(store,'func (s *dsObjectStore) Init() error {','func (s *dsObjectStore) initBase() error {')
add('pkg/lib/localstore/objectstore/spaceindex/pinkha_torah.go','''package spaceindex

import (
 torahindex "github.com/anyproto/anytype-heart/core/pinkha/torahindex"
)

func (s *dsObjectStore) Init() error {
 if err:=s.initBase();err!=nil{return err}
 s.torahInitMu.Lock()
 defer s.torahInitMu.Unlock()
 if s.torah!=nil{return nil}
 index:=torahindex.New(s.spaceId,s.objects,s.WriteTx,s.updateObjectDetails)
 // initBase has released s.lock; post-commit notification delivery takes it.
 if err:=index.Recover(s.componentCtx);err!=nil{return err}
 s.torah=index
 return nil
}

func (s *dsObjectStore) nativeTorah()*torahindex.Index {
 s.torahInitMu.Lock();defer s.torahInitMu.Unlock()
 return s.torah
}
''')
update='pkg/lib/localstore/objectstore/spaceindex/update.go'
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
(args.output/'native-heart-integration.json').write_text(json.dumps(dict(heart_sha=PIN,patch_sha256=hashlib.sha256(patch_bytes).hexdigest(),status='PENDING_EXACT_OWNER_APPROVAL_NOT_APPLIED',files=inventory),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(patch=str(args.output/'native-heart-integration.patch'),sha256=hashlib.sha256(patch_bytes).hexdigest(),files=len(inventory))))
