package common
import "errors"
import "github.com/anyproto/anytype-heart/core/domain"
import sb "github.com/anyproto/anytype-heart/pkg/lib/core/smartblock"
var ErrCancel=errors.New("fixture import cancellation")
var ErrFileLoad=errors.New("fixture original file load category")
type Key struct {Path,Key string}
type FileInfo struct {FileId string; EncryptionKeys []Key}
type Data struct {Details *domain.Details; FileInfo *FileInfo}
type FileKeys struct {Hash string; Keys map[string]string}
type NativeSnapshot struct {SbType sb.SmartBlockType; Data *Data; FileKeys []FileKeys}
type Snapshot struct {Id string; Snapshot *NativeSnapshot}
type ConvertError struct {All []error}
func (e *ConvertError) Add(err error) {e.All=append(e.All,err)}
func (e *ConvertError) Error() error {return errors.Join(e.All...)}
