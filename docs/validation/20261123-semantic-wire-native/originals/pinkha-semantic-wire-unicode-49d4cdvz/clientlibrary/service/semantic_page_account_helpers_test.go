package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

// Exact original account helper declarations; no original Test function is copied or selected.
const t2VisibleToken = "t2visiblejournalcontrolc729"

type t2AccountState struct {
	AccountID       string
	SpaceID         string
	DocumentID      string
	BlockID         string
	RootID          string
	OperationID     string
	OperationSHA256 string
	ClaimID         string
	ChangeID        string
	RawChanges      map[string]string
	Heads           []string
}

type t2AccountRPC struct {
	t     *testing.T
	calls map[string]int
}

func (r *t2AccountRPC) raw(call func([]byte) []byte, request, response proto.Message) {
	r.t.Helper()
	name := strings.TrimSuffix(strings.TrimPrefix(reflect.TypeOf(request).Elem().Name(), "Rpc"), "Request")
	r.calls[name]++
	data, err := proto.Marshal(request)
	require.NoError(r.t, err, "marshal native request")
	require.NoError(r.t, proto.Unmarshal(call(data), response), "decode native response")
}

func (r *t2AccountRPC) check(response proto.Message) {
	r.t.Helper()
	field := reflect.ValueOf(response).Elem().FieldByName("Error")
	if field.IsValid() && !field.IsNil() && field.Elem().FieldByName("Code").Int() != 0 {
		// Never print wallet request/response values or a recovered secret.
		r.t.Fatalf("%T returned native error code %d", response, field.Elem().FieldByName("Code").Int())
	}
}

func (r *t2AccountRPC) invoke(call func([]byte) []byte, request, response proto.Message) {
	r.raw(call, request, response)
	r.check(response)
}

func t2Hash(data []byte) string {
	value := sha256.Sum256(data)
	return hex.EncodeToString(value[:])
}

func t2WriteFresh(t *testing.T, path string, data []byte) {
	t.Helper()
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err, "fresh controller-owned output required")
	_, err = file.Write(data)
	require.NoError(t, err)
	require.NoError(t, file.Sync())
	require.NoError(t, file.Close())
}

func (r *t2AccountRPC) wait(label string, predicate func() bool) {
	r.t.Helper()
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		if predicate() {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
	r.t.Fatal("native account lifecycle timeout: " + label)
}

func t2Space(t *testing.T, id string) clientspace.Space {
	t.Helper()
	require.NotNil(t, mw.GetApp(), "real native account must be running")
	spc, err := app.MustComponent[space.Service](mw.GetApp()).Get(context.Background(), id)
	require.NoError(t, err)
	require.Equal(t, id, spc.Id())
	return spc
}

func (r *t2AccountRPC) show(spaceID, id string) *pb.RpcObjectShowResponse {
	r.t.Helper()
	response := &pb.RpcObjectShowResponse{}
	r.invoke(ObjectShow, &pb.RpcObjectShowRequest{SpaceId: spaceID, ObjectId: id, ContextId: id}, response)
	require.NotNil(r.t, response.ObjectView)
	require.Equal(r.t, id, response.ObjectView.RootId)
	return response
}

func t2ShownDetails(t *testing.T, shown *pb.RpcObjectShowResponse, state *t2AccountState) *domain.Details {
	t.Helper()
	for _, row := range shown.ObjectView.Details {
		if row.Id == state.DocumentID {
			details := domain.NewDetailsFromProto(row.Details)
			require.Equal(t, state.DocumentID, details.GetString(bundle.RelationKeyId))
			require.Equal(t, state.SpaceID, details.GetString(bundle.RelationKeySpaceId))
			return details
		}
	}
	t.Fatal("ordinary target details missing from actual ObjectShow")
	return nil
}

func (r *t2AccountRPC) search(state *t2AccountState, fulltext, id string) []string {
	r.t.Helper()
	request := &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID, FullText: fulltext, Keys: []string{"id"}, Limit: 100}
	if id != "" {
		request.Filters = []*model.BlockContentDataviewFilter{{RelationKey: "id",
			Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String(id).ToProto()}}
	}
	response := &pb.RpcObjectSearchResponse{}
	r.invoke(ObjectSearch, request, response)
	ids := []string{}
	for _, record := range response.Records {
		value := domain.NewDetailsFromProto(record).GetString(bundle.RelationKeyId)
		require.NotEmpty(r.t, value)
		ids = append(ids, value)
	}
	sort.Strings(ids)
	return ids
}

func (r *t2AccountRPC) createTarget(state *t2AccountState) {
	createdSpace := &pb.RpcWorkspaceCreateResponse{}
	r.invoke(WorkspaceCreate, &pb.RpcWorkspaceCreateRequest{Details: domain.NewDetails().
		SetString(bundle.RelationKeyName, "T2 disposable native lifecycle").ToProto()}, createdSpace)
	state.SpaceID = createdSpace.SpaceId
	require.NotEmpty(r.t, state.SpaceID)
	r.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: state.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
	// Readiness is a read-only precondition. Never retry object creation after
	// an ambiguous native response. Wait for Page in the actual native index.
	r.wait("indexed native Page type", func() bool {
		response := &pb.RpcObjectSearchResponse{}
		r.invoke(ObjectSearch, &pb.RpcObjectSearchRequest{SpaceId: state.SpaceID,
			Filters: []*model.BlockContentDataviewFilter{{RelationKey: "uniqueKey",
				Condition: model.BlockContentDataviewFilter_Equal, Value: domain.String("ot-page").ToProto()}},
			Keys: []string{"id", "spaceId", "uniqueKey"}, Limit: 2}, response)
		if len(response.Records) == 0 {
			return false
		}
		require.Len(r.t, response.Records, 1, "unambiguous native Page type required")
		d := domain.NewDetailsFromProto(response.Records[0])
		require.Equal(r.t, state.SpaceID, d.GetString(bundle.RelationKeySpaceId))
		require.Equal(r.t, "ot-page", d.GetString(bundle.RelationKeyUniqueKey))
		require.NotEmpty(r.t, d.GetString(bundle.RelationKeyId))
		return true
	})
	created := &pb.RpcObjectCreateResponse{}
	r.invoke(ObjectCreate, &pb.RpcObjectCreateRequest{SpaceId: state.SpaceID, ObjectTypeUniqueKey: "ot-page",
		Details: domain.NewDetails().SetString(bundle.RelationKeyName, t2VisibleToken).ToProto()}, created)
	state.DocumentID = created.ObjectId
	require.NotEmpty(r.t, state.DocumentID)
	block := &pb.RpcBlockCreateResponse{}
	r.invoke(BlockCreate, &pb.RpcBlockCreateRequest{ContextId: state.DocumentID, TargetId: state.DocumentID,
		Position: model.Block_Inner, Block: &model.Block{Content: &model.BlockContentOfText{
			Text: &model.BlockContentText{Text: t2VisibleToken}}}}, block)
	state.BlockID = block.BlockId
	require.NotEmpty(r.t, state.BlockID)
}
