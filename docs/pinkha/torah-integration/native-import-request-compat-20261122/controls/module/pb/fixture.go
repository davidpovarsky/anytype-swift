package pb
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type RpcObjectImportRequest struct { SpaceId string; Type model.Import; Mode int }
const RpcObjectImportRequest_ALL_OR_NOTHING = 1
const RpcObjectImportRequest_IGNORE_ERRORS = 2
