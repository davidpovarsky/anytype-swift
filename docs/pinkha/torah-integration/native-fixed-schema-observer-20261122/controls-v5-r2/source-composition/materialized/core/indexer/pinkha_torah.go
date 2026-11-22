package indexer

import (
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 values "github.com/anyproto/anytype-heart/core/pinkha/torahvalues"
 "github.com/anyproto/anytype-heart/pkg/lib/localstore/ftsearch"
)

func (i *indexer) withoutTorahCanonicalText(details,indexed *domain.Details)*domain.Details{
 if indexed==nil{return details}
 key:=indexed.GetString(domain.RelationKey(torah.CanonicalKeyKey))
 if key==""{return details}
 return details.CopyWithoutKeys(domain.RelationKey(key))
}

func (i *indexer) prepareTorahSearchDocs(id domain.FullID,details *domain.Details)(docs []ftsearch.SearchDoc){
 if details==nil{return nil}
 texts:=values.SearchTexts(details)
 for _,definition:=range torah.Definitions{
  text:=texts[definition.Key]
  if text!=""{docs=append(docs,ftsearch.SearchDoc{Id:domain.NewObjectPathWithRelation(id.ObjectID,definition.Key).String(),SpaceId:id.SpaceID,Text:text})}
 }
 return docs
}
