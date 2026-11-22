package objectstore
import "github.com/anyproto/anytype-heart/core/domain"
type ObjectStore interface {AddFileKeys(domain.FileEncryptionKeys) error}
