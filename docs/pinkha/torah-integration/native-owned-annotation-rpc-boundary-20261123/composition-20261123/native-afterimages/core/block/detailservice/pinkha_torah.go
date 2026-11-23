package detailservice

import (
 "context"
 "fmt"
 "github.com/anyproto/anytype-heart/core/block/cache"
 "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 "github.com/anyproto/anytype-heart/core/session"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func (s *service) AttachTorahProperties(ctx session.Context,id string,keys []string) error {
 return cache.Do(s.objectGetter,id,func(object smartblock.SmartBlock)error{
  if err:=checkDetailsEditable(object);err!=nil{return err}
  st:=object.NewStateCtx(ctx)
  projector,ok:=s.store.SpaceIndex(object.SpaceID()).(interface{TorahLocalDetails(context.Context,*domain.Details)(*domain.Details,error)})
  if !ok{return fmt.Errorf("native Torah projection unavailable")}
  details,err:=projector.TorahLocalDetails(context.Background(),st.CombinedDetails())
  if err!=nil{return err}
  if details==nil || !details.GetBool(domain.RelationKey(torah.ReadyKey)){return fmt.Errorf("Torah properties require a normal document in a provisioned Space")}
  for _,key:=range keys{
   if !torah.IsProperty(key){return fmt.Errorf("not a native Torah property: %s",key)}
   st.AddRelationLinks(&model.RelationLink{Key:key,Format:model.RelationFormat_tag})
  }
  return object.Apply(st)
 })
}
