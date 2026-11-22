package model
type BlockContentFileType int32
type BlockContentFileState int32
const BlockContentFile_Uploading BlockContentFileState=1
type ImportType int32
func (i ImportType) String() string { return "fixture_pb" }
type Bookmark struct { TargetObjectId, Url string }
type Text struct { IconImage string }
func (t *Text) GetIconImage() string {return t.IconImage}
type Block struct { Bookmark *Bookmark; File any; Text *Text }
func (b *Block) GetBookmark() *Bookmark {return b.Bookmark}
func (b *Block) GetFile() any {return b.File}
func (b *Block) GetText() *Text {return b.Text}
