package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync-sdk/auth"
	"github.com/anyproto/any-sync-sdk/config"
	"github.com/anyproto/any-sync-sdk/internal/anysyncx"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/recordverifier"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
	"github.com/anyproto/any-sync/commonspace/spacesyncproto"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/util/crypto"
	"storj.io/drpc"
)

var privateTreePeers = []string{
	"12D3KooWSuLvzhQ4BWYxY44RhofekVMj4K1zrWbXuBuN3fEyQDSF",
	"12D3KooWLnrfwmFNZZALAc6SXURBh1usyUmBH1hxG4Xk4cmrXmau",
	"12D3KooWB6owA1PYqS4knkRsyAJPYerVp98CUdpvfa2fQwbwE4GS",
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func summary(acl list.AclList) map[string]interface{} {
	rows := []map[string]interface{}{}
	for _, r := range acl.Records() {
		rows = append(rows, map[string]interface{}{"id": r.Id, "prevId": r.PrevId, "identity": r.Identity.Account(), "modelType": fmt.Sprintf("%T", r.Model)})
	}
	reqs, err := acl.AclState().JoinRecords(false)
	must(err)
	joins := []map[string]interface{}{}
	for _, r := range reqs {
		joins = append(joins, map[string]interface{}{"recordId": r.RecordId, "identity": r.RequestIdentity.Account(), "keyRecordId": r.KeyRecordId, "type": r.Type})
	}
	return map[string]interface{}{"aclId": acl.Id(), "head": acl.Head().Id, "records": rows, "count": len(rows), "joinRequests": joins}
}

func main() {
	if len(os.Args) != 7 {
		panic("expected copied wallet, copied database, space id, verified original nodeconf, independent app state, expected account id")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 70*time.Second)
	defer cancel()
	wallet, dbPath, sid, nodeconfPath, dataDir, wantAccount := os.Args[1], os.Args[2], os.Args[3], os.Args[4], os.Args[5], os.Args[6]
	if _, err := os.Stat(wallet); err != nil {
		panic(err)
	}
	provider, err := auth.NewFileProvider(auth.FileProviderConfig{Path: wallet})
	must(err)
	if provider.Created() {
		panic("must load exact retained credentials")
	}
	seed, err := provider.AccountKey(ctx)
	must(err)
	key, err := crypto.UnmarshalEd25519PrivateKey(seed)
	must(err)
	if key.GetPublic().Account() != wantAccount {
		panic("retained identity mismatch")
	}
	nodeconf, err := os.ReadFile(nodeconfPath)
	must(err)
	off := false
	cfg := config.Config{Storage: config.Storage{DataDir: dataDir}, Network: config.Network{NodeConfYAML: nodeconf}, Sync: config.Sync{DialTimeout: 3 * time.Second}, P2P: config.P2P{Enabled: &off, LocalDiscovery: &off}, Headless: true}
	app, err := anysyncx.New(ctx, cfg, provider)
	must(err)
	defer func() {
		closeCtx, closeCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer closeCancel()
		must(app.Close(closeCtx))
	}()
	db, err := anystore.Open(ctx, dbPath, &anystore.Config{ReadConnections: 1})
	must(err)
	defer db.Close()
	st, err := spacestorage.New(ctx, sid, db)
	must(err)
	localStorage, err := st.AclStorage()
	must(err)
	networkKey, err := crypto.DecodeNetworkId("N72HQKYajADVPoyw2XXtyTScBYR7SwkudRULgED4CYyHdphU")
	must(err)
	local, err := list.BuildAclListWithIdentity(app.AccountKeys(), localStorage, recordverifier.New(networkKey))
	must(err)
	rows := []map[string]interface{}{}
	for _, peerID := range privateTreePeers {
		row := map[string]interface{}{"requestedPeerID": peerID, "method": "SpaceSync.AclGetRecords", "aclHead": "", "signedChainValidated": false}
		started := time.Now()
		readCtx, readCancel := context.WithTimeout(ctx, 15*time.Second)
		var records []*consensusproto.RawRecordWithId
		p, readErr := app.Pool().Get(readCtx, peerID)
		if readErr == nil {
			readErr = p.DoDrpc(readCtx, func(conn drpc.Conn) error {
				response, callErr := spacesyncproto.NewDRPCSpaceSyncClient(conn).AclGetRecords(readCtx, &spacesyncproto.AclGetRecordsRequest{SpaceId: sid, AclHead: ""})
				if callErr != nil {
					return callErr
				}
				if len(response.Records) == 0 || len(response.Records) > 64 {
					return fmt.Errorf("unexpected bounded retained ACL record count: %d", len(response.Records))
				}
				for _, raw := range response.Records {
					record := &consensusproto.RawRecordWithId{}
					if callErr = record.UnmarshalVT(raw); callErr != nil {
						return callErr
					}
					records = append(records, record)
				}
				return nil
			})
		}
		readCancel()
		row["seconds"] = time.Since(started).Seconds()
		if readErr != nil {
			row["error"] = readErr.Error()
		} else {
			storage, storageErr := list.NewInMemoryStorage(records[0].Id, records)
			if storageErr != nil {
				row["error"] = storageErr.Error()
			} else {
				remote, verifyErr := list.BuildAclListWithIdentity(app.AccountKeys(), storage, recordverifier.New(networkKey))
				if verifyErr != nil {
					row["error"] = verifyErr.Error()
				} else {
					row["signedChainValidated"] = true
					row["acl"] = summary(remote)
					row["sameACLRoot"] = local.Id() == remote.Id()
					row["sameHead"] = local.Head().Id == remote.Head().Id
				}
			}
		}
		rows = append(rows, row)
	}
	out := map[string]interface{}{"status": "DIRECT_NODE_SIGNED_ACL_DIAGNOSTIC_NOT_MEMBERSHIP_ACCEPTANCE", "account": wantAccount, "space": sid, "local": summary(local), "nodes": rows, "mutatingRPCs": 0}
	data, err := json.Marshal(out)
	must(err)
	fmt.Println(string(data))
}
