package file
import "github.com/anyproto/anytype-heart/core/block/simple"
import "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
type Block interface { simple.Block; SetState(model.BlockContentFileState); Copy() simple.Block }
