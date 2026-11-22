package cache
import "context"
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
type ObjectGetter interface {
 GetObject(context.Context,string)(smartblock.SmartBlock,error)
 GetObjectByFullID(context.Context,domain.FullID)(smartblock.SmartBlock,error)
}
