// A new conditional-update phase on the SAME original two-process fixture.
// It does not rerun the completed plain roundtrip, generate another account,
// copy native bodies between peers, or treat a local receipt as remote delivery.
package application_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/anytype/config"
	"github.com/anyproto/anytype-heart/core/application"
	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/export"
	importer "github.com/anyproto/anytype-heart/core/block/import"
	"github.com/anyproto/anytype-heart/core/block/simple/base"
	"github.com/anyproto/anytype-heart/core/event"
	"github.com/anyproto/anytype-heart/metrics"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/gogo/protobuf/proto"
	"github.com/google/uuid"
)

type originalNetworkRevisionPointer struct {
	RootSHA  string `json:"root_sha256"`
	BlockID  string `json:"changed_block_id,omitempty"`
	BlockSHA string `json:"changed_block_sha256,omitempty"`
}

type originalNetworkRevisionBaseline struct {
	Round    int    `json:"round"`
	RootSHA  string `json:"root_sha256"`
	Accepted bool   `json:"accepted"`
}

func TestOtzariaOriginalNetworkRevisionPeer(t *testing.T) {
	role := os.Getenv("OTZARIA_ORIGINAL_REVISION_ROLE")
	root := os.Getenv("OTZARIA_ORIGINAL_NETWORK_ROOT")
	run := os.Getenv("OTZARIA_ORIGINAL_REVISION_RUN")
	reopen := strings.HasSuffix(role, "-reopen")
	phase := strings.TrimSuffix(role, "-reopen")
	if (phase != "producer" && phase != "consumer") || !filepath.IsAbs(root) || !filepath.IsAbs(run) {
		t.Fatal("explicit original existing peer role/root and fresh revision phase required")
	}
	for _, directory := range []string{root, run} {
		info, err := os.Lstat(directory)
		if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm()&0077 != 0 {
			t.Fatal("owned private native fixture directory required")
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Minute)
	defer cancel()
	// A peer failure cancels only this test's own original operation context.
	// The deferred real AccountStop still executes and its receipt is retained.
	go originalNetworkRevisionWatchAbort(ctx, run, cancel)
	var pointer originalNetworkPointer
	originalNetworkWaitJSON(t, ctx, root, "source-pointer.json", &pointer)
	repo := filepath.Join(root, phase+"-repository")
	info, err := os.Lstat(repo)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		t.Fatal("the existing original peer repository is required")
	}
	evidence := filepath.Join(run, role)
	if err := os.Mkdir(evidence, 0700); err != nil {
		t.Fatal("revision evidence phase must be fresh: ", err)
	}
	service := application.New()
	service.SetClientVersion("otzaria-original-revision-network-acceptance", "1.0.0")
	service.SetEventSender(event.NewCallbackSender(func(*pb.Event) {}))
	metrics.Service.SetPlatform("test")
	metrics.Service.SetStartVersion("1.0.0")
	metrics.Service.InitWithKeys(metrics.DefaultInHouseKey)
	defer func() {
		stopErr := service.AccountStop(&pb.RpcAccountStopRequest{RemoveData: false})
		originalNetworkJSON(t, evidence, "stop.json", map[string]any{
			"returned": stopErr == nil, "application_absent": service.GetApp() == nil,
		})
		if stopErr != nil {
			t.Errorf("actual original AccountStop failed: %v", stopErr)
		}
	}()
	credential, err := os.ReadFile(filepath.Join(root, "development-mnemonic.private"))
	if err != nil {
		t.Fatal("private existing development credential unavailable")
	}
	if err := service.WalletRecover(&pb.RpcWalletRecoverRequest{RootPath: repo, Mnemonic: string(credential)}); err != nil {
		t.Fatal("original recovery of existing private identity failed")
	}
	account, err := service.AccountSelect(ctx, &pb.RpcAccountSelectRequest{
		Id: pointer.AccountID, RootPath: repo, PreferredSpaceId: pointer.SpaceID,
		DisableLocalNetworkSync: true, NetworkMode: pb.RpcAccount_DefaultConfig,
	})
	if err != nil || account == nil || account.Id != pointer.AccountID {
		t.Fatalf("actual original existing account selection failed: %v", err)
	}
	native := service.GetApp()
	if native == nil {
		t.Fatal("actual original native app missing")
	}
	actual := app.MustComponent[accountservice.Service](native).Account().SignKey.GetPublic().Account()
	cfg := app.MustComponent[*config.Config](native)
	if actual != pointer.AccountID || cfg.NetworkMode == pb.RpcAccount_LocalOnly || !cfg.DontStartLocalNetworkSyncAutomatically {
		t.Fatal("actual account/default remote network/LAN exclusion differs")
	}
	f := &ownedClosedFixture{ctx: ctx, service: service, nativeApp: native, directory: repo,
		evidence: evidence, accountID: pointer.AccountID}
	f.blocks = app.MustComponent[*block.Service](native)
	f.exporter = app.MustComponent[export.Export](native)
	f.spaces = app.MustComponent[space.Service](native)
	originalNetworkWaitSpace(t, f, pointer.SpaceID)
	originalNetworkJSON(t, evidence, "process.json", map[string]any{
		"pid": os.Getpid(), "role": role, "repository": repo,
		"same_account": pointer.AccountID, "same_space": pointer.SpaceID, "same_object": pointer.ObjectID,
		"network_mode": int32(cfg.NetworkMode), "lan_sync_disabled": true,
		"new_account_created": false, "existing_repository_recovered": true,
	})

	if reopen {
		var final originalNetworkRevisionPointer
		originalNetworkWaitJSON(t, ctx, run, "consumer-applied-pointer.json", &final)
		observed := originalNetworkAwaitRevision(t, f, pointer, "cold-read", final.RootSHA, "")
		if observed.Status != "read" || observed.NativeApplyAttempted || observed.NativeWriteObserved {
			t.Fatal("cold read unexpectedly mutated native object")
		}
		originalNetworkJSON(t, evidence, "accepted.json", map[string]any{
			"actual_fresh_process_reopen": true, "same_native_root": pointer.ObjectID,
			"root_sha256": observed.RootSHA, "native_heads": observed.Heads,
			"read_only": true, "pid": os.Getpid(), "remote_network_ack": false,
			"archive_object_id": observed.ArchiveID, "archive_heads": observed.ArchiveHeads,
			"is_archived": *observed.IsArchived,
		})
		return
	}

	// Retained repositories can start with different locally materialized revisions.
	// Agree only through genuine fresh native reads; never copy a body or write a
	// replacement merely to manufacture a shared baseline.
	baseline := originalNetworkAgreeRevisionBaseline(t, f, pointer, run, phase)
	originalNetworkJSON(t, evidence, "baseline-pointer.json", originalNetworkRevisionPointer{RootSHA: baseline.RootSHA})
	if phase == "producer" {
		originalNetworkJSON(t, run, "producer-baseline-pointer.json", originalNetworkRevisionPointer{RootSHA: baseline.RootSHA})
		var ready originalNetworkRevisionPointer
		originalNetworkWaitJSON(t, ctx, run, "consumer-token-ready.json", &ready)
		if ready.RootSHA != baseline.RootSHA {
			t.Fatal("peer baseline content differs")
		}
		blockID, blockSHA := originalNetworkCreateText(t, f, pointer.ObjectID, "שינוי עמית מקורי "+uuid.NewString())
		changed := originalNetworkAwaitRevision(t, f, pointer, "producer-change", "", blockID)
		originalNetworkJSON(t, run, "producer-change-pointer.json", originalNetworkRevisionPointer{
			RootSHA: changed.RootSHA, BlockID: blockID, BlockSHA: blockSHA,
		})
		var applied originalNetworkRevisionPointer
		originalNetworkWaitJSON(t, ctx, run, "consumer-applied-pointer.json", &applied)
		observed := originalNetworkAwaitRevision(t, f, pointer, "remote-conditional-readback", applied.RootSHA, "")
		originalNetworkRequireSameBlocks(t, baseline.NativeArchive, observed.NativeArchive, pointer.ObjectID, pointer.SpaceID)
		if originalNetworkRevisionHasBlock(t, observed.NativeArchive, pointer, blockID) {
			t.Fatal("original conditional replacement did not remove the explicitly replaced peer change")
		}
		peerReadback := map[string]any{
			"status":           "ACTUAL_OTHER_PROCESS_NATIVE_REVISION_READBACK",
			"same_native_root": pointer.ObjectID, "root_sha256": observed.RootSHA,
			"native_heads": observed.Heads, "pid": os.Getpid(),
			"archive_object_id": observed.ArchiveID, "archive_heads": observed.ArchiveHeads,
			"is_archived": *observed.IsArchived,
			"complete_original_baseline_blocks_equal": true, "changed_peer_block_absent": true,
			"native_local_receipt_used_as_network_ack": false,
		}
		originalNetworkJSON(t, run, "producer-remote-revision-readback.json", peerReadback)
		originalNetworkJSON(t, evidence, "accepted.json", peerReadback)
	} else {
		var producerBase originalNetworkRevisionPointer
		originalNetworkWaitJSON(t, ctx, run, "producer-baseline-pointer.json", &producerBase)
		baseline = originalNetworkAwaitRevision(t, f, pointer, "matching-baseline", producerBase.RootSHA, "")
		originalNetworkJSON(t, run, "consumer-token-ready.json", originalNetworkRevisionPointer{RootSHA: baseline.RootSHA})
		var change originalNetworkRevisionPointer
		originalNetworkWaitJSON(t, ctx, run, "producer-change-pointer.json", &change)
		remote := originalNetworkAwaitRevision(t, f, pointer, "actual-remote-change", change.RootSHA, change.BlockID)
		originalNetworkRequireTextHash(t, remote.NativeArchive, pointer, change.BlockID, change.BlockSHA)
		// Saved desired bytes come from THIS receiver's own previous genuine
		// original export. No body/archive is supplied by the control channel.
		desired := &ownedClosedSpecimen{Raw: baseline.NativeArchive, Digest: sha256.Sum256(baseline.NativeArchive),
			RootID: pointer.ObjectID, SourceSpace: pointer.SpaceID}
		stale, operationErr := revisionNativeCall(t, f, "remote-stale-conflict", pointer.ObjectID, pointer.AnnotationUUID, desired, baseline)
		if !errors.Is(operationErr, importer.ErrAnnotationRevisionConflict) || stale.Status != "conflict" ||
			stale.NativeApplyAttempted || stale.NativeWriteObserved {
			t.Fatalf("remotely invalidated native token was not refused before Apply: %v", operationErr)
		}
		after := originalNetworkAwaitRevision(t, f, pointer, "after-conflict", remote.RootSHA, change.BlockID)
		originalNetworkRequirePresentArchiveWitness(t, f, stale)
		if !slices.Equal(after.Heads, stale.Heads) || after.RootSHA != stale.RootSHA ||
			after.ArchiveID != stale.ArchiveID || !slices.Equal(after.ArchiveHeads, stale.ArchiveHeads) ||
			*after.IsArchived != *stale.IsArchived {
			t.Fatal("conflict changed original root or Archive revision")
		}
		originalNetworkJSON(t, evidence, "explicit-resolution-choice.json", map[string]any{
			"test_action":                "explicitly choose previously saved original baseline after observed conflict",
			"desired_archive_sha256":     hex.EncodeToString(desired.Digest[:]),
			"fresh_observed_root_sha256": after.RootSHA, "fresh_heads": after.Heads,
			"archive_object_id": after.ArchiveID, "archive_heads": after.ArchiveHeads,
			"is_archived":             *after.IsArchived,
			"automatic_product_retry": false, "old_token_reused": false,
		})
		// This is a separate explicit conflict-resolution test action with a
		// newly read token, never an automatic product retry of the old attempt.
		applied, operationErr := revisionNativeCall(t, f, "explicit-conditional-apply", pointer.ObjectID, pointer.AnnotationUUID, desired, after)
		if operationErr != nil || applied.Status != "applied" || !applied.NativeApplyAttempted ||
			!applied.NativeWriteObserved || applied.RootID != pointer.ObjectID {
			t.Fatalf("actual original conditional replacement failed: %v", operationErr)
		}
		originalNetworkRequirePresentArchiveWitness(t, f, applied)
		if applied.ArchiveID != after.ArchiveID || !slices.Equal(applied.ArchiveHeads, after.ArchiveHeads) {
			t.Fatal("conditional root replacement changed the original Archive tree")
		}
		originalNetworkRequireSameBlocks(t, baseline.NativeArchive, applied.NativeArchive, pointer.ObjectID, pointer.SpaceID)
		originalNetworkJSON(t, run, "consumer-applied-pointer.json", originalNetworkRevisionPointer{RootSHA: applied.RootSHA})
		var actualPeer map[string]any
		originalNetworkWaitJSON(t, ctx, run, "producer-remote-revision-readback.json", &actualPeer)
		if actualPeer["status"] != "ACTUAL_OTHER_PROCESS_NATIVE_REVISION_READBACK" ||
			actualPeer["same_native_root"] != pointer.ObjectID || actualPeer["root_sha256"] != applied.RootSHA ||
			actualPeer["native_local_receipt_used_as_network_ack"] != false {
			t.Fatal("the actual other-process receipt does not bind this conditional update")
		}
		originalNetworkJSON(t, evidence, "accepted.json", map[string]any{
			"actual_remote_change_observed_before_stale_compare":        true,
			"stale_native_compare_refused_without_apply_or_head_change": true,
			"explicit_resolution_uses_fresh_token":                      true, "actual_conditional_original_apply": true,
			"same_native_root": pointer.ObjectID, "root_sha256": applied.RootSHA,
			"archive_object_id": applied.ArchiveID, "archive_heads": applied.ArchiveHeads,
			"is_archived": *applied.IsArchived, "archive_cas_witness_bound": true,
			"independent_peer_readback_observed": true, "pid": os.Getpid(),
			"native_local_receipt_used_as_network_ack": false,
		})
	}
}

// The request/response control files carry only revision hashes and round
// decisions. Both peers retain their OWN original archive and locked token.
// Account recovery and real remote transport can legitimately converge retained
// repositories after startup; a stale first export is never an eternal target.
func originalNetworkAgreeRevisionBaseline(t *testing.T, f *ownedClosedFixture,
	p originalNetworkPointer, run, role string) nativeRevisionWire {
	t.Helper()
	for round := 0; ; round++ {
		probeName := fmt.Sprintf("baseline-probe-%03d.json", round)
		replyName := fmt.Sprintf("baseline-reply-%03d.json", round)
		decisionName := fmt.Sprintf("baseline-decision-%03d.json", round)
		if role == "producer" {
			probe := originalNetworkAwaitRevision(t, f, p, fmt.Sprintf("baseline-probe-%03d", round), "", "")
			originalNetworkJSON(t, run, probeName, originalNetworkRevisionBaseline{Round: round, RootSHA: probe.RootSHA})
			var reply originalNetworkRevisionBaseline
			originalNetworkWaitJSON(t, f.ctx, run, replyName, &reply)
			if reply.Round != round {
				t.Fatal("original peer baseline reply round differs")
			}
			current := originalNetworkAwaitRevision(t, f, p, fmt.Sprintf("baseline-confirm-%03d", round), "", "")
			accepted := probe.RootSHA == current.RootSHA && reply.RootSHA == current.RootSHA
			originalNetworkJSON(t, run, decisionName, originalNetworkRevisionBaseline{
				Round: round, RootSHA: current.RootSHA, Accepted: accepted,
			})
			if accepted {
				return current
			}
		} else {
			var probe originalNetworkRevisionBaseline
			originalNetworkWaitJSON(t, f.ctx, run, probeName, &probe)
			if probe.Round != round {
				t.Fatal("original peer baseline probe round differs")
			}
			current := originalNetworkAwaitRevision(t, f, p, fmt.Sprintf("baseline-receiver-%03d", round), "", "")
			originalNetworkJSON(t, run, replyName, originalNetworkRevisionBaseline{Round: round, RootSHA: current.RootSHA})
			var decision originalNetworkRevisionBaseline
			originalNetworkWaitJSON(t, f.ctx, run, decisionName, &decision)
			if decision.Round != round {
				t.Fatal("original peer baseline decision round differs")
			}
			if decision.Accepted {
				if decision.RootSHA != current.RootSHA || decision.RootSHA != probe.RootSHA {
					t.Fatal("baseline acceptance does not match both original native observations")
				}
				return originalNetworkAwaitRevision(t, f, p,
					fmt.Sprintf("baseline-receiver-confirm-%03d", round), decision.RootSHA, "")
			}
		}
		select {
		case <-f.ctx.Done():
			t.Fatal("original peers did not reach a genuine shared baseline")
		case <-time.After(500 * time.Millisecond):
		}
	}
}

func originalNetworkRequirePresentArchiveWitness(t *testing.T, f *ownedClosedFixture, value nativeRevisionWire) {
	t.Helper()
	if value.ArchiveID != f.spc.DerivedIDs().Archive || value.ArchiveID == value.RootID ||
		value.IsArchived == nil || *value.IsArchived || len(value.ArchiveHeads) == 0 ||
		!slices.IsSorted(value.ArchiveHeads) {
		t.Fatal("actual present-root Archive witness is missing or differs from the original Space")
	}
	for index, head := range value.ArchiveHeads {
		if head == "" || (index > 0 && head == value.ArchiveHeads[index-1]) {
			t.Fatal("actual Archive heads must be nonempty, sorted and unique")
		}
	}
}

func originalNetworkAwaitRevision(t *testing.T, f *ownedClosedFixture, p originalNetworkPointer,
	label, expectedHash, requiredBlock string) nativeRevisionWire {
	t.Helper()
	for n := 0; ; n++ {
		value, err := revisionNativeCall(t, f, label+"-"+time.Now().UTC().Format("150405.000000000"), p.ObjectID, p.AnnotationUUID, nil, nativeRevisionWire{})
		matches := err == nil && value.Status == "read" && (expectedHash == "" || value.RootSHA == expectedHash)
		if matches && requiredBlock != "" {
			matches = originalNetworkRevisionHasBlock(t, value.NativeArchive, p, requiredBlock)
		}
		if matches {
			originalNetworkRequirePresentArchiveWitness(t, f, value)
			if value.NativeApplyAttempted || value.NativeWriteObserved {
				t.Fatal("a native read reported a mutation")
			}
			return value
		}
		select {
		case <-f.ctx.Done():
			t.Fatalf("actual original revision observation not reached: %v", err)
		case <-time.After(2 * time.Second):
		}
	}
}
func originalNetworkRevisionHasBlock(t *testing.T, raw []byte, p originalNetworkPointer, id string) bool {
	t.Helper()
	snapshot := revisionNativeRoot(t, raw, p.SpaceID, p.ObjectID)
	for _, b := range snapshot.Snapshot.Data.Blocks {
		if b != nil && b.Id == id {
			return true
		}
	}
	return false
}
func originalNetworkRequireSameBlocks(t *testing.T, first, second []byte, root, spaceID string) {
	t.Helper()
	a := revisionNativeRoot(t, first, spaceID, root)
	b := revisionNativeRoot(t, second, spaceID, root)
	left := map[string]*model.Block{}
	for _, block := range a.Snapshot.Data.Blocks {
		if block == nil || block.Id == "" || left[block.Id] != nil {
			t.Fatal("invalid original saved block inventory")
		}
		left[block.Id] = originalNetworkRevisionCanonicalBlock(t, block)
	}
	if len(left) != len(b.Snapshot.Data.Blocks) {
		t.Fatal("native full block inventory differs from selected saved body")
	}
	seen := map[string]bool{}
	for _, block := range b.Snapshot.Data.Blocks {
		if block == nil || seen[block.Id] {
			t.Fatal("invalid actual original block inventory")
		}
		seen[block.Id] = true
		expected, ok := left[block.Id]
		if !ok || !proto.Equal(expected, originalNetworkRevisionCanonicalBlock(t, block)) {
			t.Fatal("original block identity/content/complete marks/child order differ")
		}
	}
}

// Original Text.Diff/marksEq sorts the actual old/new mark inventories during
// Apply. Compare only that array's order canonically by each COMPLETE protobuf
// tuple, exactly as revision canonicalRevisionSnapshot. Preserve duplicates,
// ranges, types, parameters and unknown fields. The original Base.Diff additionally
// equates absent and all-false restrictions by materializing an empty message;
// invoke that same original helper on private comparison copies. Every nonempty
// restriction and every other block field remain exact. The genuine ZIP hashes and native locked revision token remain separate witnesses.
func originalNetworkRevisionCanonicalBlock(t *testing.T, original *model.Block) *model.Block {
	t.Helper()
	if original == nil {
		t.Fatal("nil native block")
	}
	block := proto.Clone(original).(*model.Block)
	other := proto.Clone(block).(*model.Block)
	changes, err := base.NewBase(block).Diff("", base.NewBase(other))
	if err != nil || len(changes) != 0 {
		t.Fatal("original block self-comparison changed native content")
	}
	marks := block.GetText().GetMarks()
	if marks == nil {
		return block
	}
	type tuple struct {
		mark *model.BlockContentTextMark
		raw  []byte
	}
	ordered := make([]tuple, len(marks.Marks))
	for i, mark := range marks.Marks {
		if mark == nil {
			t.Fatal("nil native text mark")
		}
		raw, err := proto.Marshal(mark)
		if err != nil {
			t.Fatal(err)
		}
		ordered[i] = tuple{mark: mark, raw: raw}
	}
	sort.SliceStable(ordered, func(i, j int) bool { return bytes.Compare(ordered[i].raw, ordered[j].raw) < 0 })
	for i, item := range ordered {
		marks.Marks[i] = item.mark
	}
	return block
}

func TestOtzariaOriginalNetworkRevisionCanonicalRestrictions(t *testing.T) {
	original := &model.Block{Id: "exact-original-block", ChildrenIds: []string{"first", "second"}}
	empty := proto.Clone(original).(*model.Block)
	empty.Restrictions = &model.BlockRestrictions{}
	if !proto.Equal(originalNetworkRevisionCanonicalBlock(t, original),
		originalNetworkRevisionCanonicalBlock(t, empty)) {
		t.Fatal("original Base.Diff empty restriction equivalence is missing")
	}
	if original.Restrictions != nil || !proto.Equal(empty.Restrictions, &model.BlockRestrictions{}) {
		t.Fatal("comparison mutated the actual saved input")
	}
	for name, restriction := range map[string]*model.BlockRestrictions{
		"read": {Read: true}, "edit": {Edit: true}, "remove": {Remove: true},
		"drag": {Drag: true}, "drop_on": {DropOn: true},
	} {
		t.Run(name, func(t *testing.T) {
			changed := proto.Clone(original).(*model.Block)
			changed.Restrictions = restriction
			if proto.Equal(originalNetworkRevisionCanonicalBlock(t, original),
				originalNetworkRevisionCanonicalBlock(t, changed)) {
				t.Fatal("a genuine nonzero native restriction was discarded")
			}
			if !proto.Equal(changed.Restrictions, restriction) {
				t.Fatal("comparison modified the actual restriction")
			}
		})
	}
	changed := proto.Clone(original).(*model.Block)
	changed.ChildrenIds[0], changed.ChildrenIds[1] = changed.ChildrenIds[1], changed.ChildrenIds[0]
	if proto.Equal(originalNetworkRevisionCanonicalBlock(t, original),
		originalNetworkRevisionCanonicalBlock(t, changed)) {
		t.Fatal("ordered native child relations were discarded")
	}
}

func originalNetworkRequireTextHash(t *testing.T, raw []byte, p originalNetworkPointer, id, want string) {
	t.Helper()
	snapshot := revisionNativeRoot(t, raw, p.SpaceID, p.ObjectID)
	for _, b := range snapshot.Snapshot.Data.Blocks {
		if b == nil || b.Id != id || b.GetText() == nil {
			continue
		}
		body, err := proto.Marshal(originalNetworkRevisionCanonicalBlock(t, b).GetText())
		if err != nil {
			t.Fatal(err)
		}
		actual := sha256.Sum256(body)
		if hex.EncodeToString(actual[:]) != want {
			t.Fatal("remote original rich text/marks hash differs")
		}
		return
	}
	t.Fatal("remote original changed text block missing")
}

func originalNetworkRevisionWatchAbort(ctx context.Context, run string, cancel context.CancelFunc) {
	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			_, err := os.Lstat(filepath.Join(run, "abort.json"))
			if err == nil || !os.IsNotExist(err) {
				cancel()
				return
			}
		}
	}
}
