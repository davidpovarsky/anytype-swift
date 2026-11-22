package domain
import "iter"
type RelationKey string
type FileId string
type FullID struct { SpaceID, ObjectID string }
type FullFileId struct { SpaceId string; FileId FileId }
type FileEncryptionKeys struct { FileId FileId; EncryptionKeys map[string]string }
type Details struct { Values map[RelationKey]string }
func NewDetails() *Details { return &Details{Values:map[RelationKey]string{}} }
func (d *Details) GetString(k RelationKey) string { if d==nil{return ""}; return d.Values[k] }
func (d *Details) Set(k RelationKey,v string) { d.Values[k]=v }
func (d *Details) Iterate() iter.Seq2[RelationKey,string] { return func(yield func(RelationKey,string) bool) {for k,v:=range d.Values {if !yield(k,v){return}}} }
func (d *Details) ToProto() any {return d}
