//go:build pinkha_acl_transport_fixture

package core

import (
	"context"

	"github.com/anyproto/anytype-heart/pb"
)

// PinkhaMemberACLFixturePrepare exists only in the separately compiled native
// acceptance binary. It preserves the real preparation/finalization code and
// lets the controller interleave an observed network ACL update between them.
// It supplies no authority, callback, snapshot, or replacement result.
func (mw *Middleware) PinkhaMemberACLFixturePrepare(ctx context.Context, spaceID, operationID string) (func() *pb.PinkhaTorahAuthorizedOperationReadResponse, error) {
	prepared, err := mw.preparePinkhaAuthorizedOperationRead(ctx, PinkhaTorahAuthorizedOperationReadRequest{
		Version: 1, SpaceID: spaceID, OperationID: operationID,
	})
	if err != nil {
		return nil, err
	}
	return func() *pb.PinkhaTorahAuthorizedOperationReadResponse { return prepared.wire(ctx) }, nil
}
