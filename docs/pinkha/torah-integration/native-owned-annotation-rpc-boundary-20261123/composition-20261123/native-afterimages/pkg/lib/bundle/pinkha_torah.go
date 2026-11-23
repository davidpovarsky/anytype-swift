package bundle

import (
 "github.com/anyproto/anytype-heart/core/domain"
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 "github.com/anyproto/anytype-heart/pkg/lib/localstore/addr"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Package variables precede init(): the native local/derived key lists include
// these immutable list properties. No option objects or global installed rows.
var pinkhaTorahRegistered = func() bool {
 for _,d:=range torah.Definitions {
  key:=domain.RelationKey(d.Key)
  relations[key]=&model.Relation{Id:addr.BundledRelationURLPrefix+d.Key,
   Key:d.Key,Name:d.Name,Format:model.RelationFormat_tag,
   DataSource:model.Relation_derived,ReadOnly:true,ReadOnlyRelation:true,
   Scope:model.Relation_type,MaxCount:0}
 }
 // Private capability/label/readiness fields use the same native exclusion
 // rules as derived properties for CRDT snapshots, export and local injection.
 for _,key:=range torah.LocalKeys()[3:] {
  format:=model.RelationFormat_longtext
  if key==torah.ReadyKey{format=model.RelationFormat_checkbox}
  if key==torah.VersionKey{format=model.RelationFormat_number}
  relations[domain.RelationKey(key)]=&model.Relation{Id:addr.BundledRelationURLPrefix+key,
   Key:key,Name:key,Format:format,Hidden:true,
   DataSource:model.Relation_derived,ReadOnly:true,ReadOnlyRelation:true,Scope:model.Relation_type}
 }
 return true
}()
