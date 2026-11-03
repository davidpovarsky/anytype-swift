package heartprobe

import (
 "context"
 "encoding/json"
 "path/filepath"
 "testing"

 anystore "github.com/anyproto/any-store"
 "github.com/anyproto/any-store/anyenc"
 "github.com/anyproto/any-store/query"
 "github.com/anyproto/anytype-heart/core/domain"
 "github.com/anyproto/anytype-heart/pkg/lib/bundle"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
 engine "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/engine"
 torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

// This verifies the actual production index lifecycle against native SQLite.
// Product API/Set acceptance must additionally run against the approved patched
// Heart. Do not promote this component result to D01-D34 product acceptance.
func TestProductionEngineLifecycleAndRecovery(t *testing.T) {
 ctx:=context.Background()
 path:=filepath.Join(t.TempDir(),"native.db")
 var db anystore.DB
 var objects anystore.Collection
 var index *engine.Index
 var raw engine.Writer
 open:=func(){
  var err error
  db,err=anystore.Open(ctx,path,nil);if err!=nil{t.Fatal(err)}
  objects,err=db.Collection(ctx,"objects");if err!=nil{t.Fatal(err)}
  raw=func(ctx context.Context,id string,d *domain.Details)error{
   d=d.Copy().SetString(bundle.RelationKeyId,id)
   _,err:=objects.UpsertId(ctx,id,query.ModifyFunc(func(a *anyenc.Arena,_ *anyenc.Value)(*anyenc.Value,bool,error){return d.ToAnyEnc(a),true,nil}))
   return err
  }
  index=engine.New("s",objects,db.WriteTx,raw)
  if err=index.Recover(ctx);err!=nil{t.Fatal(err)}
 }
 open()
 defer func(){db.Close()}()
 put:=func(id string,d *domain.Details){t.Helper();if err:=index.Update(ctx,id,d);err!=nil{t.Fatal(err)}}
 get:=func(id string)*domain.Details{t.Helper();doc,err:=objects.FindId(ctx,id);if err!=nil{t.Fatal(err)};d,err:=domain.NewDetailsFromAnyEnc(doc.Value());if err!=nil{t.Fatal(err)};return d}
 manifest:=map[string]any{
  "schemaVersion":1,"spaceId":"s","manifestObjectId":"manifest","provisioningState":"complete",
  "documentAssociationsPropertyId":"canonical-property","documentAssociationsPropertyKey":"customCanonical",
  "registeredDocumentTypes":map[string]string{"chiddush":"h","article":"a","research":"r"},
  "defaultTemplateIds":map[string]string{"chiddush":"th","article":"ta","research":"tr"},
  "parentPropertyId":"parent","parentPropertyKey":"parentKey","orderPropertyId":"order","orderPropertyKey":"orderKey",
  "folderTypeId":"folder","bookFolderTypeId":"book",
 }
 putManifest:=func(){payload,_:=json.Marshal(manifest);put("manifest",domain.NewDetails().SetString(bundle.RelationKeyName,torah.ManifestUniqueKey).SetString(bundle.RelationKeySpaceId,"s").SetString(bundle.RelationKeyDescription,string(payload)))}
 put("canonical-property",domain.NewDetails().SetString(bundle.RelationKeyRelationKey,"customCanonical").SetInt64(bundle.RelationKeyRelationFormat,0).SetInt64(bundle.RelationKeyLayout,int64(model.ObjectType_relation)))
 document:=func(raw string)*domain.Details{return domain.NewDetails().SetString(bundle.RelationKeySpaceId,"s").SetStringList(bundle.RelationKeyType,[]string{"h"}).SetString("customCanonical",raw)}
 payload:=`{"version":1,"items":[{"id":"source","kind":"ref","role":"context","providerID":"sefaria","canonicalKey":"Genesis 1:1","externalID":"Genesis 1:1","labelHe":"בראשית א:א"}]}`
 put("doc",document(payload))
 if get("doc").Has(torah.SourcesKey){t.Fatal("unbound document was projected")}
 putManifest()
 identity:=torah.Identity(torah.Ref,"sefaria","Genesis 1:1","")
 if got:=get("doc").GetStringList(torah.SourcesKey);len(got)!=1||got[0]!=identity{t.Fatalf("manifest upgrade failed: %v",got)}
 if get("manifest").GetInt64(torah.VersionKey)!=1{t.Fatal("no native capability")}
 if get("doc").GetString("customCanonical")!=payload{t.Fatal("canonical bytes changed")}
 if !get("doc").GetBool(torah.ReadyKey){t.Fatal("eligible document not ready")}
 forged:=document(payload).SetStringList(torah.SourcesKey,[]string{"forged"})
 put("doc",forged)
 if get("doc").GetStringList(torah.SourcesKey)[0]!=identity{t.Fatal("forged derived value accepted")}
 tx,err:=db.WriteTx(ctx);if err!=nil{t.Fatal(err)}
 if err=index.Update(tx.Context(),"doc",document(""));err!=nil{t.Fatal(err)}
 if err=tx.Rollback();err!=nil{t.Fatal(err)}
 if get("doc").GetString("customCanonical")!=payload{t.Fatal("nested rollback changed canonical")}
 // A candidate-ID hint introduced by an outer tx is not binding state. Once
 // rolled back, it must not poison future resolution or Space readiness.
 tx,err=db.WriteTx(ctx);if err!=nil{t.Fatal(err)}
 duplicate:=map[string]any{};for key,value:=range manifest{duplicate[key]=value};duplicate["manifestObjectId"]="rolled-back-manifest"
 duplicateRaw,_:=json.Marshal(duplicate)
 if err=index.Update(tx.Context(),"rolled-back-manifest",domain.NewDetails().SetString(bundle.RelationKeyName,torah.ManifestUniqueKey).SetString(bundle.RelationKeyDescription,string(duplicateRaw)));err!=nil{t.Fatal(err)}
 if err=tx.Rollback();err!=nil{t.Fatal(err)}
 put("doc",document(payload))
 if !get("doc").GetBool(torah.ReadyKey){t.Fatal("rolled-back candidate poisoned binding cache")}
 put("doc",document(payload).SetBool(bundle.RelationKeyIsArchived,true))
 if get("doc").GetBool(torah.ReadyKey)||get("doc").Has(torah.SourcesKey){t.Fatal("archived membership retained")}
 put("doc",document(payload))
 if !get("doc").GetBool(torah.ReadyKey){t.Fatal("unarchive did not restore canonical membership")}
 put("malformed",document(`{"version":900}`))
 if get("malformed").GetBool(torah.ReadyKey)||get("malformed").Has(torah.SourcesKey){t.Fatal("future payload matched empty/negative predicates")}
 put("foreign",document(payload).SetString(bundle.RelationKeySpaceId,"foreign"))
 if get("foreign").GetBool(torah.ReadyKey){t.Fatal("foreign Space indexed")}
 // Simulate a missing/stale local index, retaining the only canonical source.
 if err=raw(ctx,"doc",document(payload));err!=nil{t.Fatal(err)}
 if err=db.Close();err!=nil{t.Fatal(err)}
 open()
 if get("doc").GetStringList(torah.SourcesKey)[0]!=identity{t.Fatal("relaunch recovery failed")}
 if get("doc").GetString(torah.LabelsKey)==""{t.Fatal("labels not rebuilt")}
 plan,err:=objects.Find(map[string]any{torah.SourcesKey:identity}).Explain(ctx);if err!=nil{t.Fatal(err)}
 indexed:=false;for _,idx:=range plan.Indexes{indexed=indexed||(idx.Name==torah.SourcesKey&&idx.Used)}
 if !indexed{t.Fatalf("native membership index not used: %+v",plan)}
 manifest["registeredDocumentTypes"]=map[string]string{"chiddush":"new-h","article":"a","research":"r"}
 putManifest()
 if get("doc").GetBool(torah.ReadyKey)||get("doc").Has(torah.SourcesKey){t.Fatal("old Type membership survived manifest change")}
 if get("doc").GetString("customCanonical")!=payload{t.Fatal("rebind rewrote associations")}
 manifest["registeredDocumentTypes"]=map[string]string{"chiddush":"h","article":"a","research":"r"}
 putManifest()
 if err=index.Delete(ctx,[]string{"canonical-property"},func(ctx context.Context)error{return objects.DeleteId(ctx,"canonical-property")});err!=nil{t.Fatal(err)}
 if get("doc").GetBool(torah.ReadyKey)||get("manifest").Has(torah.VersionKey){t.Fatal("deleted canonical property left ready state")}
 count,err:=objects.Count(ctx);if err!=nil{t.Fatal(err)}
 if count!=4{t.Fatalf("unexpected generated objects/options: %d",count)}
}
