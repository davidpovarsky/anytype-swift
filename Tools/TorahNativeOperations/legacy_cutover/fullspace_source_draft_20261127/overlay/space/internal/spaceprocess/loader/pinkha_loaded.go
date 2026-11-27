package loader

import (
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/torahindexcontract"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/space/internal/components/spaceloader"
)

// PinkhaLoaded uses the already registered component. No child app is started.
// sameProcess binds the concrete original loader across controller transitions.
func PinkhaLoaded(current any) (sp clientspace.Space, validate func() error, sameProcess func(any) bool, deliver torahindexcontract.DeliveryFence, err error) {
	l, ok := current.(*loader)
	if !ok || l.app == nil {
		return nil, nil, nil, nil, torahindexcontract.ErrNotLoaded
	}
	component, err := app.GetComponent[spaceloader.SpaceLoader](l.app)
	if err != nil {
		return nil, nil, nil, nil, err
	}
	sp, validate, deliver, err = spaceloader.PinkhaLoaded(component)
	if err != nil {
		return nil, nil, nil, nil, err
	}
	return sp, validate, func(candidate any) bool { other, ok := candidate.(*loader); return ok && other == l }, deliver, nil
}
