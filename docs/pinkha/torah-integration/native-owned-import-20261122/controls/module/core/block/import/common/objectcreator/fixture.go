package objectcreator
import "github.com/anyproto/anytype-heart/core/domain"
import "github.com/anyproto/anytype-heart/core/block/import/common"
type Service interface {Create(*DataObject,*common.Snapshot)(*domain.Details,string,error)}
type FixtureService func(*DataObject,*common.Snapshot)(*domain.Details,string,error)
func (s FixtureService) Create(d *DataObject,n *common.Snapshot)(*domain.Details,string,error){return s(d,n)}
