package main

import (
 "context"
 "encoding/json"
 "fmt"
 "os"
 "time"
 anystore "github.com/anyproto/any-store"
 "github.com/anyproto/any-sync/commonspace/spacestorage"
 "github.com/anyproto/any-sync/commonspace/object/acl/list"
 "github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
 "github.com/anyproto/any-sync/util/crypto"
 "github.com/anyproto/any-sync-sdk/auth"
 "github.com/anyproto/any-sync-sdk/config"
 "github.com/anyproto/any-sync-sdk/internal/anysyncx"
)
func must(err error) { if err!=nil {panic(err)} }
func summary(acl list.AclList) map[string]interface{} {
 rows:=[]map[string]interface{}{}
 for _,r:=range acl.Records() {rows=append(rows,map[string]interface{}{"id":r.Id,"prevId":r.PrevId,"identity":r.Identity.Account(),"modelType":fmt.Sprintf("%T",r.Model)})}
 reqs,err:=acl.AclState().JoinRecords(false);must(err)
 joins:=[]map[string]interface{}{}
 for _,r:=range reqs {joins=append(joins,map[string]interface{}{"recordId":r.RecordId,"identity":r.RequestIdentity.Account(),"keyRecordId":r.KeyRecordId,"type":r.Type})}
 return map[string]interface{}{"aclId":acl.Id(),"head":acl.Head().Id,"records":rows,"count":len(rows),"joinRequests":joins}
}
func main(){
 if len(os.Args)!=7 {panic("expected copied wallet, copied database, space id, verified nodeconf, independent app state, expected account id")}
 ctx,cancel:=context.WithTimeout(context.Background(),50*time.Second);defer cancel()
 wallet,dbPath,sid,nodeconfPath,dataDir,wantAccount:=os.Args[1],os.Args[2],os.Args[3],os.Args[4],os.Args[5],os.Args[6]
 if _,err:=os.Stat(wallet);err!=nil {panic(err)}
 provider,err:=auth.NewFileProvider(auth.FileProviderConfig{Path:wallet});must(err);if provider.Created(){panic("must load exact retained credentials")}
 seed,err:=provider.AccountKey(ctx);must(err);key,err:=crypto.UnmarshalEd25519PrivateKey(seed);must(err)
 if key.GetPublic().Account()!=wantAccount {panic("retained identity mismatch")}
 nodeconf,err:=os.ReadFile(nodeconfPath);must(err)
 off:=false
 cfg:=config.Config{Storage:config.Storage{DataDir:dataDir},Network:config.Network{NodeConfYAML:nodeconf},Sync:config.Sync{DialTimeout:3*time.Second},P2P:config.P2P{Enabled:&off,LocalDiscovery:&off},Headless:true}
 app,err:=anysyncx.New(ctx,cfg,provider);must(err)
 defer func(){c,stop:=context.WithTimeout(context.Background(),10*time.Second);defer stop();must(app.Close(c))}()
 db,err:=anystore.Open(ctx,dbPath,&anystore.Config{ReadConnections:1});must(err);defer db.Close()
 st,err:=spacestorage.New(ctx,sid,db);must(err);storage,err:=st.AclStorage();must(err)
 network,err:=crypto.DecodeNetworkId("N72HQKYajADVPoyw2XXtyTScBYR7SwkudRULgED4CYyHdphU");must(err)
 local,err:=list.BuildAclListWithIdentity(app.AccountKeys(),storage,recordverifier.New(network));must(err)
 remote,err:=app.AclSnapshot(ctx,sid);must(err)
 out:=map[string]interface{}{"status":"VERIFIED_ACL_DIAGNOSTIC_NOT_FILE_ACCEPTANCE","account":wantAccount,"space":sid,"local":summary(local),"network":summary(remote),"sameACLRoot":local.Id()==remote.Id(),"sameHead":local.Head().Id==remote.Head().Id}
 data,err:=json.Marshal(out);must(err);fmt.Println(string(data))
}
