package fileobject
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/domain/objectorigin"
type Service interface {CreateFromImport(domain.FullFileId,objectorigin.ObjectOrigin,*domain.Details)(string,error)}
