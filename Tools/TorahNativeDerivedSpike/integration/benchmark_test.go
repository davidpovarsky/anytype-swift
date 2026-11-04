package heartprobe

import (
 "context"
 "encoding/json"
 "fmt"
 "io/fs"
 "os"
 "path/filepath"
 "runtime"
 "sort"
 "sync/atomic"
 "syscall"
 "testing"
 "time"

 "github.com/anyproto/anytype-heart/core/domain"
 "github.com/anyproto/anytype-heart/pkg/lib/bundle"
 "github.com/anyproto/anytype-heart/pkg/lib/database"
 "github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
 torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

type trackingTB struct { *testing.T; dirs []string }
func(t *trackingTB)TempDir()string{d:=t.T.TempDir();t.dirs=append(t.dirs,d);return d}
func(t *trackingTB)bytes()int64{
 var size int64
 for _,dir:=range t.dirs{if err:=filepath.WalkDir(dir,func(_ string,e fs.DirEntry,err error)error{
  if err!=nil{return err};if e.IsDir(){return nil};info,err:=e.Info();if err==nil{size+=info.Size()};return err
 });err!=nil{t.Fatal(err)}}
 return size
}
func percentile(samples []time.Duration,p int)float64{
 values:=append([]time.Duration(nil),samples...);sort.Slice(values,func(i,j int)bool{return values[i]<values[j]})
 return float64(values[(len(values)-1)*p/100])/float64(time.Millisecond)
}
func benchmarkPayload(t testing.TB,n,fanout int,removeFirst bool)string{
 t.Helper();id:=fmt.Sprintf("doc-%06d",n);records:=[]any{}
 add:=func(kind,provider,key,role string,block bool){
  item:=map[string]string{"id":fmt.Sprintf("link-%d",len(records)),"kind":kind,"role":role,"providerID":provider,"canonicalKey":key,"externalID":key,"labelHe":"מקור בדיקה"}
  record:=map[string]any{"spaceId":"test","objectId":id,"item":item};if block{record["blockId"]="preserved-block"};records=append(records,record)
 }
 for j:=0;j<fanout;j++{
  if j==0&&removeFirst{continue}
  key:=fmt.Sprintf("unique-%d-%d",n,j);if j==0{key=fmt.Sprintf("shared-%d",n%10)}
  provider:="sefaria";if j%2==1{provider="otzaria"};add("ref",provider,key,"context",false)
 }
 add("topic","sefaria",fmt.Sprintf("topic-%d",n%7),"context",false)
 add("word","sefaria",fmt.Sprintf("word-%d",n%11),"context",false)
 add("ref","sefaria","block-only","context",true)
 add("ref","sefaria","quoted-only","sourceQuote",false)
 add("ref","sefaria","anytype-note:excluded","context",false)
 data,err:=json.Marshal(map[string]any{"version":2,"records":records});if err!=nil{t.Fatal(err)};return string(data)
}

// Actual production native hooks; never prefill Sources/Ready in the fixture.
// Baseline is this same pinned patched engine in an unbound Space. It is an
// explicit local-engine control, not an unmodified-old-binary or iPad baseline.
func TestNativeBenchmarks(t *testing.T){
 if os.Getenv("PINKHA_NATIVE_BENCH")!="1"{t.Skip("explicit synthetic benchmark opt-in required")}
 for _,count:=range []int{100,2000,10000,50000}{for _,fanout:=range []int{2,10,50}{
  t.Run(fmt.Sprintf("documents-%d-links-%d",count,fanout),func(t *testing.T){
   ctx:=context.Background();baselineTB,derivedTB:=&trackingTB{T:t},&trackingTB{T:t}
   baseline,store:=spaceindex.NewStoreFixture(baselineTB),spaceindex.NewStoreFixture(derivedTB)
   // The upstream fixture closes its DB provider but has no worker lifecycle.
   // Close the real stores first, including the native outbox workers.
   t.Cleanup(func(){store.Close();baseline.Close()})
   installNativeBinding(t,baseline,false);manifest:=installNativeBinding(t,store,false)
   var nativeWrites atomic.Int64
   store.SubscribeForAll(func(database.Record){nativeWrites.Add(1)})
   var beforeMemory,afterMemory runtime.MemStats;runtime.ReadMemStats(&beforeMemory)
   var beforeCPU,afterCPU syscall.Rusage;_ = syscall.Getrusage(syscall.RUSAGE_SELF,&beforeCPU)
   write:=func(target spaceindex.Store)time.Duration{
    started:=time.Now()
    for start:=0;start<count;start+=500{
     tx,err:=target.WriteTx(ctx);if err!=nil{t.Fatal(err)}
     for n:=start;n<min(start+500,count);n++{
      details:=nativeFixtureDocument(benchmarkPayload(t,n,fanout,false))
      details.SetString(bundle.RelationKeyType,[]string{"chiddush","article","research"}[n%3])
      if err=target.UpdateObjectDetails(tx.Context(),fmt.Sprintf("doc-%06d",n),details);err!=nil{t.Fatal(err)}
     }
     if err=tx.Commit();err!=nil{t.Fatal(err)}
    };return time.Since(started)
   }
   baselineWrite,unboundWrite:=write(baseline),write(store)
   beforeRebuildBytes:=derivedTB.bytes();writesBeforeRebuild:=nativeWrites.Load()
   manifest.SetString(bundle.RelationKeyName,torah.ManifestUniqueKey)
   started:=time.Now()
   if err:=store.UpdateObjectDetails(ctx,"fixture-manifest",manifest);err!=nil{t.Fatal(err)}
   rebuild:=time.Since(started);rebuildWrites:=nativeWrites.Load()-writesBeforeRebuild
   filters:=&database.Filters{FilterObj:database.FilterIn{Key:sources,Value:[]domain.Value{domain.String(torah.Identity(torah.Ref,"sefaria","shared-1",""))}}}
   latencies:=make([]time.Duration,100)
   for n:=range latencies{
    started=time.Now();total,err:=store.CountRaw(filters);if err!=nil{t.Fatal(err)}
    if total!=count/10{t.Fatalf("membership false positives/negatives: %d",total)}
    page,err:=store.QueryRaw(filters,25,0);if err!=nil{t.Fatal(err)}
    if len(page)!=min(25,count/10){t.Fatal("paging mismatch")};latencies[n]=time.Since(started)
   }
   incremental:=make([]time.Duration,50)
   updates:=make(chan *domain.Details,4)
   sub:=database.NewSubscription(nil,updates)
   records,closeSub,err:=store.QueryByIdsAndSubscribeForChanges([]string{"doc-000000"},sub);if err!=nil{t.Fatal(err)}
   if len(records)!=1{t.Fatal("native subscription missing document")};defer closeSub()
   subscriptionLatencies:=[]time.Duration{}
   for n:=range incremental{
    started=time.Now()
    if err:=store.UpdateObjectDetails(ctx,"doc-000000",nativeFixtureDocument(benchmarkPayload(t,0,fanout,n%2==0)));err!=nil{t.Fatal(err)}
    incremental[n]=time.Since(started)
    select{case delivered:=<-updates:
     subscriptionLatencies=append(subscriptionLatencies,time.Since(started))
     want:=fanout;if n%2==0{want--};if len(delivered.GetStringList(sources))!=want{t.Fatal("stale native subscription projection")}
    case<-time.After(5*time.Second):t.Fatal("missing native subscription notification")}
   }
   d,err:=store.GetDetails("doc-000000");if err!=nil{t.Fatal(err)}
   if !d.GetBool(ready)||len(d.GetStringList(sources))!=fanout{t.Fatal("projection fanout or restore mismatch")}
   for _,target:=range []spaceindex.Store{baseline,store}{
    total,err:=target.CountRaw(&database.Filters{FilterObj:database.FilterExists{Key:bundle.RelationKeyId}});if err!=nil{t.Fatal(err)}
    if total!=count+2{t.Fatalf("Object explosion: expected exactly documents + two metadata rows; got %d",total)}
   }
   runtime.ReadMemStats(&afterMemory);_ = syscall.Getrusage(syscall.RUSAGE_SELF,&afterCPU)
   cpuUS:=func(r syscall.Rusage)int64{return r.Utime.Sec*1000000+int64(r.Utime.Usec)+r.Stime.Sec*1000000+int64(r.Stime.Usec)}
   row:=map[string]any{"documents":count,"document_refs":fanout,"additional_kind_and_block_records":5,"metadata_objects":2,
    "baseline_unbound_write_ms":baselineWrite.Milliseconds(),"candidate_unbound_write_ms":unboundWrite.Milliseconds(),"full_native_rebuild_ms":rebuild.Milliseconds(),
    "native_rebuild_write_notifications":rebuildWrites,"total_native_write_notifications":nativeWrites.Load(),
    "baseline_files_bytes":baselineTB.bytes(),"derived_files_before_rebuild_bytes":beforeRebuildBytes,"derived_files_bytes":derivedTB.bytes(),
    "query_count_plus_page_p50_ms":percentile(latencies,50),"query_count_plus_page_p95_ms":percentile(latencies,95),"query_count_plus_page_p99_ms":percentile(latencies,99),
    "incremental_p50_ms":percentile(incremental,50),"incremental_p95_ms":percentile(incremental,95),"incremental_p99_ms":percentile(incremental,99),
    "native_subscription_p95_ms":percentile(subscriptionLatencies,95),"allocated_bytes":afterMemory.TotalAlloc-beforeMemory.TotalAlloc,"heap_after_bytes":afterMemory.HeapAlloc,
    "process_cpu_ms":float64(cpuUS(afterCPU)-cpuUS(beforeCPU))/1000,"host_os":runtime.GOOS,"host_arch":runtime.GOARCH,"cpus":runtime.NumCPU(),"go":runtime.Version(),
    "scope":"production native ObjectStore projection/index/rebuild and commit notifications; not app UI/iPad or unmodified binary baseline"}
   encoded,err:=json.Marshal(row);if err!=nil{t.Fatal(err)};fmt.Printf("PINKHA_NATIVE_BENCHMARK %s\n",encoded)
  })
 }}
}
