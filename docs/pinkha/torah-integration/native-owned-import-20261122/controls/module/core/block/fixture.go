package block
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
