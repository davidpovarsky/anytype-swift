package objectid
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
