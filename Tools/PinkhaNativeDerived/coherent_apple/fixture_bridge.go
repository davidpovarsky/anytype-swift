//go:build pinkha_coherent_apple_fixture

// This bridge is absent from the separately built production framework.
package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"sync"

	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
)

var coherentAppleBridgeSHA = "UNSET"
var coherentAppleCallMutex sync.Mutex
var coherentAppleUsed bool
var coherentAppleRPCReplies = map[string][]byte{}

func coherentAppleRecordRPCReply(name string, raw []byte) {
	if name == "ObjectSearch" || name == "ObjectShow" {
		coherentAppleRPCReplies[name] = append([]byte(nil), raw...)
	}
}

type coherentAppleAbort struct{}
type coherentAppleT struct {
	failed bool
	location string
	cleanups []func()
}

func (t *coherentAppleT) Helper() {}
func (t *coherentAppleT) Cleanup(f func()) { t.cleanups = append(t.cleanups, f) }
func (t *coherentAppleT) abort() {
	t.failed = true
	if t.location == "" {
		for depth := 2; depth < 12; depth++ {
			_, file, line, ok := runtime.Caller(depth)
			if ok && filepath.Base(file) != "coherent_apple_fixture_bridge.go" {
				t.location = fmt.Sprintf("%s:%d", filepath.Base(file), line)
				break
			}
		}
	}
	panic(coherentAppleAbort{})
}
func (t *coherentAppleT) Fatal(_ ...any) { t.abort() }
func (t *coherentAppleT) Fatalf(_ string, _ ...any) { t.abort() }
func (t *coherentAppleT) finish() {
	for index := len(t.cleanups)-1; index >= 0; index-- {
		func() {
			defer func() { if recover() != nil { t.failed = true } }()
			t.cleanups[index]()
		}()
	}
	t.cleanups = nil
}

// The fixture uses precisely this assertion subset. Values are never included
// in exported failure diagnostics, because they could contain generated keys.
type coherentAppleAssertions struct{}
var coherentAppleRequire coherentAppleAssertions
func (coherentAppleAssertions) True(t *coherentAppleT, value bool, _ ...any) { if !value { t.abort() } }
func (coherentAppleAssertions) False(t *coherentAppleT, value bool, _ ...any) { if value { t.abort() } }
func (coherentAppleAssertions) NoError(t *coherentAppleT, value error, _ ...any) { if value != nil { t.abort() } }
func (coherentAppleAssertions) Equal(t *coherentAppleT, a, b any, _ ...any) { if !reflect.DeepEqual(a,b) { t.abort() } }
func (coherentAppleAssertions) NotEqual(t *coherentAppleT, a, b any, _ ...any) { if reflect.DeepEqual(a,b) { t.abort() } }
func coherentAppleIsNil(value any) bool {
	if value == nil { return true }
	v := reflect.ValueOf(value)
	switch v.Kind() { case reflect.Chan, reflect.Func, reflect.Interface, reflect.Map, reflect.Pointer, reflect.Slice: return v.IsNil() }
	return false
}
func (coherentAppleAssertions) Nil(t *coherentAppleT, value any, _ ...any) { if !coherentAppleIsNil(value) { t.abort() } }
func (coherentAppleAssertions) NotNil(t *coherentAppleT, value any, _ ...any) { if coherentAppleIsNil(value) { t.abort() } }
func coherentAppleEmpty(value any) bool {
	if coherentAppleIsNil(value) { return true }
	v := reflect.ValueOf(value)
	switch v.Kind() {
	case reflect.Array, reflect.Map, reflect.Slice, reflect.String, reflect.Chan: return v.Len() == 0
	default: return v.IsZero()
	}
}
func (coherentAppleAssertions) Empty(t *coherentAppleT, value any, _ ...any) { if !coherentAppleEmpty(value) { t.abort() } }
func (coherentAppleAssertions) NotEmpty(t *coherentAppleT, value any, _ ...any) { if coherentAppleEmpty(value) { t.abort() } }
func (coherentAppleAssertions) Len(t *coherentAppleT, value any, count int, _ ...any) {
	v := reflect.ValueOf(value)
	if !v.IsValid() { t.abort() }
	switch v.Kind() {
	case reflect.Array, reflect.Chan, reflect.Map, reflect.Slice, reflect.String: if v.Len() != count { t.abort() }
	default: t.abort()
	}
}
func (coherentAppleAssertions) Same(t *coherentAppleT, a, b any, _ ...any) {
	x,y := reflect.ValueOf(a),reflect.ValueOf(b)
	if !x.IsValid() || !y.IsValid() || x.Kind() != reflect.Pointer || y.Kind() != reflect.Pointer || x.Type() != y.Type() || x.Pointer() != y.Pointer() { t.abort() }
}
func (coherentAppleAssertions) LessOrEqual(t *coherentAppleT, a, b int, _ ...any) { if a>b { t.abort() } }
func (coherentAppleAssertions) Contains(t *coherentAppleT, values, sought any, _ ...any) {
	v := reflect.ValueOf(values)
	if v.Kind() != reflect.Slice && v.Kind() != reflect.Array { t.abort() }
	for i:=0;i<v.Len();i++ { if reflect.DeepEqual(v.Index(i).Interface(),sought) { return } }
	t.abort()
}

// PinkhaCoherentAppleAuthorityFixture is a one-shot, test-tag-only bridge.
// It creates its own temporary account root; it never accepts a caller path.
// No active account may exist. The generated native RPCs and signed ACL
// validators/updater used by the original fixture are unchanged.
func PinkhaCoherentAppleAuthorityFixture(request []byte) (response []byte) {
	coherentAppleCallMutex.Lock()
	defer coherentAppleCallMutex.Unlock()
	failed := func(location string) []byte {
		value,_ := json.Marshal(map[string]any{"status":"FAIL_COHERENT_APPLE_FIXTURE","failure_location":location})
		return value
	}
	response = failed("preflight")
	t := &coherentAppleT{}
	owned := false
	defer func() {
		if recover() != nil { t.failed = true }
		t.finish()
		if owned && mw.GetApp() != nil {
			// A failure between native account creation and its normal cleanup
			// registration must not strand this newly created synthetic account.
			t.failed = true
			func() {
				defer func() { _ = recover() }()
				stop,_ := proto.Marshal(&pb.RpcAccountStopRequest{RemoveData:false})
				AccountStop(stop)
				shutdown,_ := proto.Marshal(&pb.RpcAppShutdownRequest{})
				AppShutdown(shutdown)
			}()
		}
		if t.failed || mw.GetApp() != nil { response = failed(t.location) }
	}()
	if coherentAppleUsed || mw.GetApp() != nil || len(request)>4096 { return response }
	coherentAppleUsed = true
	var config struct {
		Nonce string `json:"nonce"`
		BridgeSHA string `json:"bridge_sha256"`
		RuntimeVersion string `json:"runtime_version"`
	}
	decoder := json.NewDecoder(bytes.NewReader(request)); decoder.DisallowUnknownFields()
	if decoder.Decode(&config) != nil || !regexp.MustCompile(`^[0-9a-f]{32}$`).MatchString(config.Nonce) ||
		!regexp.MustCompile(`^[0-9a-f]{64}$`).MatchString(coherentAppleBridgeSHA) || config.BridgeSHA != coherentAppleBridgeSHA ||
		config.RuntimeVersion != vcs.GitSummary || vcs.GitCommit != t5ACLHeart { return response }
	var trailing any
	if decoder.Decode(&trailing) != io.EOF { return response }
	owned = true
	parent,err := os.MkdirTemp("", "pinkha-coherent-ios-"+config.Nonce+"-")
	coherentAppleRequire.NoError(t,err)
	root := filepath.Join(parent,"account-root")
	coherentAppleRequire.NoError(t,os.Mkdir(root,0700))
	owner,_ := json.Marshal(map[string]any{"protocol":t5ACLProtocol,"nonce":config.Nonce,"synthetic_only":true})
	coherentAppleRequire.NoError(t,os.WriteFile(filepath.Join(parent,"ownership.json"),owner,0600))
	env := map[string]string{"PINKHA_T5_ACL_ROOT":root,"PINKHA_T5_ACL_REPORT":filepath.Join(parent,"native-observation.json"),
		"PINKHA_T5_ACL_NONCE":config.Nonce,"PINKHA_T5_ACL_OWNERSHIP":string(owner),
		"PINKHA_T5_ACL_FIXTURE_SHA256":t5ACLFixtureSHA,"PINKHA_T5_ACL_RUNTIME_VERSION":vcs.GitSummary}
	for name,value := range env {
		old,exists := os.LookupEnv(name)
		defer func(key, prior string, present bool) { if present { _=os.Setenv(key,prior) } else { _=os.Unsetenv(key) } }(name,old,exists)
		coherentAppleRequire.NoError(t,os.Setenv(name,value))
	}
	runCoherentAppleNativeReadsAfterSignedRevocation(t)
	t.finish()
	coherentAppleRequire.False(t,t.failed)
	coherentAppleRequire.Nil(t,mw.GetApp())
	secretBytes,err := os.ReadFile(filepath.Join(parent,"sensitive-needles.private"))
	coherentAppleRequire.NoError(t,err)
	var secrets []string
	coherentAppleRequire.NoError(t,json.Unmarshal(secretBytes,&secrets))
	coherentAppleRequire.Len(t,secrets,2)
	for _,secret := range secrets { coherentAppleRequire.NotEmpty(t,secret) }
	for name,filename := range map[string]string{"ObjectSearch":"object-search-removed.pb","ObjectShow":"object-show-removed.pb"} {
		coherentAppleRequire.NotEmpty(t,coherentAppleRPCReplies[name])
		coherentAuthorityWriteBytes(t,filepath.Join(parent,filename),coherentAppleRPCReplies[name])
	}
	names := []string{"ownership.json","native-observation.json","coherent-observation.json","coherent-owner.pb","coherent-reader.pb","coherent-removed.pb","object-search-removed.pb","object-show-removed.pb"}
	files := map[string][]byte{}
	hashes := map[string]string{}
	for _,name := range names {
		path:=filepath.Join(parent,name)
		info,err:=os.Lstat(path); coherentAppleRequire.NoError(t,err)
		coherentAppleRequire.True(t,info.Mode().IsRegular() && info.Size()>0 && info.Size()<2*1024*1024)
		raw,err:=os.ReadFile(path); coherentAppleRequire.NoError(t,err)
		for _,secret:=range secrets { coherentAppleRequire.False(t,bytes.Contains(raw,[]byte(secret))) }
		files[name],hashes[name]=raw,t5ACLHash(raw)
	}
	wire:=&pb.PinkhaTorahAuthorizedOperationReadResponse{}
	coherentAppleRequire.NoError(t,proto.Unmarshal(files["coherent-owner.pb"],wire))
	coherentAppleRequire.NotNil(t,wire.Snapshot)
	result:=map[string]any{"status":"PASS_ACTUAL_COHERENT_APPLE_FIXTURE","nonce":config.Nonce,"pid":os.Getpid(),
		"bridge_sha256":coherentAppleBridgeSHA,"original_fixture_sha256":t5ACLFixtureSHA,
		"runtime_version":vcs.GitSummary,"heart_sha":vcs.GitCommit,"files":files,"files_sha256":hashes,
		"account_id":wire.Snapshot.AccountId,"space_id":wire.Snapshot.SpaceId,"operation_id":wire.Snapshot.OperationId,
		"production_binary_executed":false,"fixture_tag":"pinkha_coherent_apple_fixture",
		"network_acl_transport":"NOT_RUN","full_app_acceptance":"NOT_RUN"}
	response,err=json.Marshal(result); coherentAppleRequire.NoError(t,err)
	for _,secret:=range secrets { coherentAppleRequire.False(t,bytes.Contains(response,[]byte(secret))) }
	return response
}
