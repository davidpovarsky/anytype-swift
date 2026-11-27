package spaceindex

import (
 "context"
 "github.com/anyproto/anytype-heart/core/domain"
 torahindex "github.com/anyproto/anytype-heart/core/pinkha/torahindex"
)

func (s *dsObjectStore) Init() error {
 if err:=s.initBase();err!=nil{return err}
 s.torahInitMu.Lock()
 defer s.torahInitMu.Unlock()
 if s.torah!=nil{return nil}
 var err error
 s.torahOutbox,err=s.db.Collection(s.componentCtx,"_pinkhaTorahFulltextOutbox")
 if err!=nil{return err}
 index:=torahindex.New(s.spaceId,s.objects,s.WriteTx,s.updateObjectDetails,s.db.ReadTx).WithChangeHook(s.recordTorahFulltext)
 // initBase has released s.lock; post-commit notification delivery takes it.
 if err:=index.Recover(s.componentCtx);err!=nil{return err}
 s.torah=index
 s.prepareTorahFulltext()
 s.startTorahFulltext()
 return nil
}

func (s *dsObjectStore) nativeTorah()*torahindex.Index {
 s.torahInitMu.Lock();defer s.torahInitMu.Unlock()
 return s.torah
}

func (s *dsObjectStore) TorahLocalDetails(ctx context.Context, details *domain.Details) (*domain.Details, error) {
 if index:=s.nativeTorah();index!=nil{return index.LocalDetails(ctx,details)}
 return nil,nil
}
