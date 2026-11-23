package importer

import (
	"context"
	"errors"

	"github.com/anyproto/anytype-heart/metrics"
)

// finalizeOwnedImport is used only by the private, explicitly owned processor.
// Its completion covers the local native calls and file channels admitted by
// this operation. Remote backup queues and their later status notifications are
// component-owned background work and are not drained or cleared here.
func (p *importProcessor) finalizeOwnedImport(ctx context.Context, importID string) {
	files, err := p.owned.sealAndDrain()
	p.owned.fileResults = files
	p.response.Err = errors.Join(p.response.Err, err)
	if p.response.Err == nil {
		p.addRootCollectionWidget(ctx)
	}
	p.finishImportProcess()
	recordEvent(&metrics.ImportFinishedEvent{ID: importID, ImportType: p.request.Type.String()})
	p.sendImportFinishEvent()
}
