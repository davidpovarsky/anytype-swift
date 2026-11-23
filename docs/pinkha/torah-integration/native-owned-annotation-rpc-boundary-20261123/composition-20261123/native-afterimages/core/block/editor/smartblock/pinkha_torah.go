package smartblock

import (
 "context"
 "github.com/anyproto/anytype-heart/core/block/editor/state"
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
)

func (sb *smartBlock) injectTorahDetails(s *state.State) {
 projector,ok:=sb.spaceIndex.(interface{
  TorahLocalDetails(context.Context,*domain.Details)(*domain.Details,error)
 })
 if !ok{return}
 details,err:=projector.TorahLocalDetails(context.Background(),s.CombinedDetails())
 if err!=nil {
  log.Warnf("Torah local projection unavailable: %v",err)
  details=domain.NewDetails()
 }
 if details==nil{return}
 for _,key:=range torah.LocalKeys(){s.RemoveLocalDetail(domain.RelationKey(key))}
 if details.GetBool(domain.RelationKey(torah.ReadyKey)) {
  attached:=[]string{}
  for _,link:=range s.PickRelationLinks(){
   if torah.IsProperty(link.Key){
    attached=append(attached,link.Key)
    if !details.Has(domain.RelationKey(link.Key)){details.Set(domain.RelationKey(link.Key),domain.Null())}
   }
  }
  details.SetStringList(domain.RelationKey(torah.AttachedPropertiesKey),attached)
 }
 s.AddLocalDetails(details)
}

