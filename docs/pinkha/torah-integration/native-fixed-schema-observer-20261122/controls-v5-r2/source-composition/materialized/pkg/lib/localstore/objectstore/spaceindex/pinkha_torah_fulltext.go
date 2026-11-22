package spaceindex

import (
 "context"
 "errors"
 "strings"
 "time"
 anystore "github.com/anyproto/any-store"
 "github.com/anyproto/any-store/anyenc"
 "github.com/anyproto/any-store/query"
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 values "github.com/anyproto/anytype-heart/core/pinkha/torahvalues"
)

type torahFulltextWorker struct {
 ctx context.Context
 cancel context.CancelFunc
 wake chan struct{}
 done chan struct{}
}

func(s *dsObjectStore)prepareTorahFulltext(){
 ctx,cancel:=context.WithCancel(s.componentCtx)
 s.torahFT=&torahFulltextWorker{ctx:ctx,cancel:cancel,wake:make(chan struct{},1),done:make(chan struct{})}
}

func(s *dsObjectStore)startTorahFulltext(){
 worker:=s.torahFT
 go func(){
  defer close(worker.done)
  for {
   retry:=s.drainTorahFulltext(worker.ctx)
   var timer *time.Timer
   var retryAt <-chan time.Time
   if retry {timer=time.NewTimer(5*time.Second);retryAt=timer.C}
   select {case <-worker.ctx.Done():if timer!=nil{timer.Stop()};return
    case <-worker.wake:case <-retryAt:}
   if timer!=nil{timer.Stop()}
  }
 }()
}

func(s *dsObjectStore)scheduleTorahFulltext(){
 if worker:=s.torahFT;worker!=nil{select{case worker.wake<-struct{}{}:default:}}
}

func(s *dsObjectStore)stopTorahFulltext(){
 if worker:=s.torahFT;worker!=nil{worker.cancel();<-worker.done}
}

// The outbox is in the SAME per-Space DB/transaction as canonical projection.
// It contains only document IDs and a retry token, never association payloads.
func (s *dsObjectStore) recordTorahFulltext(ctx context.Context,id string,before,after *domain.Details) error {
 native:=func(d *domain.Details)bool{return d!=nil&&d.GetString(domain.RelationKey(torah.CanonicalKeyKey))!=""}
 if !native(before)&&!native(after){return nil}
 token:=values.SearchFingerprint(after)
 if values.SearchFingerprint(before)==token{return nil}
 _,err:=s.torahOutbox.UpsertId(ctx,id,query.ModifyFunc(func(a *anyenc.Arena,_ *anyenc.Value)(*anyenc.Value,bool,error){
  value:=a.NewObject();value.Set("id",a.NewString(id));value.Set("token",a.NewString(token));return value,true,nil
 }))
 if err!=nil{return err}
 if buffer,ok:=ctx.Value(txNotificationsKey{}).(*txNotifications);ok&&buffer!=nil{
  buffer.mu.Lock();buffer.torahFulltext=true;buffer.mu.Unlock()
 }
 return nil
}

// Enqueue only AFTER the root transaction commits. Remove an outbox entry only
// after the native common-DB queue commits, and only if its token still matches.
// A crash at either boundary causes a harmless retry on the next Space open.
func (s *dsObjectStore) drainTorahFulltext(ctx context.Context) bool {
 if s.torahOutbox==nil||s.fulltextQueue==nil{return false}
 iter,err:=s.torahOutbox.Find(nil).Iter(ctx)
 if err!=nil{log.Warnf("Torah FT outbox read: %v",err);return true}
 type entry struct{id,token string}
 var pending []entry
 for iter.Next(){doc,e:=iter.Doc();if e!=nil{err=e;break};pending=append(pending,entry{strings.Clone(doc.Value().GetString("id")),strings.Clone(doc.Value().GetString("token"))})}
 if err==nil{err=iter.Err()};iter.Close()
 if err!=nil{log.Warnf("Torah FT outbox iterate: %v",err);return true}
 for start:=0;start<len(pending);start+=256{
  end:=min(start+256,len(pending));batch:=pending[start:end]
  ids:=make([]domain.FullID,0,len(batch));for _,item:=range batch{ids=append(ids,domain.FullID{SpaceID:s.spaceId,ObjectID:item.id})}
  if _,_,err=s.fulltextQueue.AddToIndexQueue(ctx,ids...);err!=nil{log.Warnf("Torah native FT enqueue: %v",err);return true}
  tx,e:=s.db.WriteTx(ctx);if e!=nil{log.Warnf("Torah FT outbox transaction: %v",e);return true}
  for _,item:=range batch{
   doc,e:=s.torahOutbox.FindId(tx.Context(),item.id)
   if errors.Is(e,anystore.ErrDocNotFound){continue}
   if e!=nil{err=e;break}
   if doc.Value().GetString("token")==item.token{if e=s.torahOutbox.DeleteId(tx.Context(),item.id);e!=nil{err=e;break}}
  }
  if err==nil{err=tx.Commit()};tx.Rollback()
  if err!=nil{log.Warnf("Torah FT outbox acknowledge: %v",err);return true}
 }
 return false
}
