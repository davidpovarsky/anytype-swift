package importer

import (
 "context"
 "encoding/json"
 "reflect"
 "testing"

 "github.com/anyproto/anytype-heart/core/block/import/common"
 "github.com/anyproto/anytype-heart/core/domain/objectorigin"
 "github.com/anyproto/anytype-heart/pb"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

func legacyRequest() *ImportRequest {
 var origin objectorigin.ObjectOrigin
 // The actual original five-position construction must remain legal Go.
 return &ImportRequest{&pb.RpcObjectImportRequest{Type:model.Import_Pb,SpaceId:"space"},origin,nil,false,true}
}

func TestOriginalPositionalRequestStillCompiles(t *testing.T) {
 r:=legacyRequest()
 names:=[]string{"RpcObjectImportRequest","Origin","Progress","SendNotification","IsSync"}
 typ:=reflect.TypeOf(*r)
 if typ.NumField()!=len(names) { t.Fatalf("request layout changed: %v",typ) }
 for i,name:=range names { if typ.Field(i).Name!=name { t.Fatalf("position %d changed",i) } }
 if r.SpaceId!="space" || !r.IsSync || r.SendNotification { t.Fatal("positional values changed") }
}

func TestLegacyConstructorDoesNotEnableCapture(t *testing.T) {
 p:=NewProcessor(&Dependencies{},legacyRequest()).(*importProcessor)
 if p.captureMappingObservation { t.Fatal("legacy constructor enabled diagnostic") }
 p.initializeNativeMappingObservation(&common.Response{})
 if p.nativeMapping!=nil || common.ProtobufSourceObservationRequested(actualConversionContext(p,context.Background())) { t.Fatal("legacy path captured") }
}

func TestExplicitPBConstructorEnablesBothCaptureBoundaries(t *testing.T) {
 deps:=&Dependencies{}
 request:=legacyRequest()
 p:=newProcessorWithNativeMappingObservation(deps,request)
 if p.deps!=deps || p.request!=request || p.response==nil || !p.captureMappingObservation { t.Fatal("opt-in lost actual ownership inputs") }
 p.initializeNativeMappingObservation(&common.Response{})
 if p.nativeMapping==nil || !common.ProtobufSourceObservationRequested(actualConversionContext(p,context.Background())) { t.Fatal("explicit PB capture not enabled at both boundaries") }
}

func TestExplicitConstructorDoesNotCaptureOtherConverter(t *testing.T) {
 request:=legacyRequest();request.Type=model.Import(99)
 p:=newProcessorWithNativeMappingObservation(&Dependencies{},request)
 p.initializeNativeMappingObservation(&common.Response{})
 if p.nativeMapping!=nil || common.ProtobufSourceObservationRequested(actualConversionContext(p,context.Background())) { t.Fatal("non-PB capture broadened") }
}

func TestResetRetainsOptInButClearsHistoricalFacts(t *testing.T) {
 p:=newProcessorWithNativeMappingObservation(&Dependencies{},legacyRequest())
 p.initializeNativeMappingObservation(&common.Response{})
 p.nativeMappingTraceID="old";p.nativeMappingSpaceID="old";p.nativeMappingAssignmentsFinished=true;p.nativeMappingCreationReturned=true;p.nativeMappingBatchesStarted=3;p.nativeMappingBatchesDrained=2;p.response.nativeMappingProblems=[]string{"old"}
 p.resetNativeMappingObservation()
 if !p.captureMappingObservation || p.nativeMapping!=nil || p.nativeMappingTraceID!="" || p.nativeMappingSpaceID!="" || p.nativeMappingAssignmentsFinished || p.nativeMappingCreationReturned || p.nativeMappingBatchesStarted!=0 || p.nativeMappingBatchesDrained!=0 || p.response.nativeMappingProblems!=nil { t.Fatal("reset confused configuration with prior execution") }
 p.initializeNativeMappingObservation(&common.Response{})
 if p.nativeMapping==nil { t.Fatal("opt-in lost on reset") }
}

func TestConstructorsDoNotShareResponseOrMutateRequest(t *testing.T) {
 request:=legacyRequest();before:=*request
 first:=newProcessorWithNativeMappingObservation(&Dependencies{},request)
 second:=NewProcessor(&Dependencies{},request).(*importProcessor)
 if first.response==second.response || !reflect.DeepEqual(before,*request) || second.captureMappingObservation { t.Fatal("constructor leaked capture or changed request") }
 first.response.ProcessId="first"
 if second.response.ProcessId!="" { t.Fatal("response state shared") }
}

func TestRequestJSONRetainsOriginalFiveFieldShape(t *testing.T) {
 request:=legacyRequest()
 got,err:=json.Marshal(request);if err!=nil {t.Fatal(err)}
 expected,err:=json.Marshal((*originalFiveFieldRequest)(request));if err!=nil {t.Fatal(err)}
 if string(got)!=string(expected) {t.Fatalf("legacy JSON changed: %s / %s",got,expected)}
 var value map[string]interface{}
 if err=json.Unmarshal(got,&value);err!=nil {t.Fatal(err)}
 if _,ok:=value["CaptureMappingObservation"];ok {t.Fatal("diagnostic leaked into request JSON")}
}
