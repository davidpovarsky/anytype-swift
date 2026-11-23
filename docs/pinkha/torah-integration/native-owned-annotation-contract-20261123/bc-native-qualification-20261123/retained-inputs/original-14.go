package importer

import (
	"fmt"

	"github.com/anyproto/anytype-heart/core/block/import/common"
	creator "github.com/anyproto/anytype-heart/core/block/import/common/objectcreator"
	"github.com/anyproto/anytype-heart/core/block/import/common/workerpool"
	"github.com/anyproto/anytype-heart/core/domain"
)

// createOwnedObjectsBatch uses the original workers and tasks. Unlike the
// legacy result reader, cancellation stops admission and still consumes the
// actual channel until the original worker WaitGroup closes it. It also joins
// the submission goroutine. This is a local-work drain, not applied-body proof.
func (p *importProcessor) createOwnedObjectsBatch(data *creator.DataObject, snapshots []*common.Snapshot) map[string]*domain.Details {
	if err := p.owned.ctx.Err(); err != nil {
		p.errors.Add(err)
		return nil
	}
	pool := workerpool.NewPool(min(workerPoolSize, len(snapshots)))
	submissionDone := make(chan struct{})
	go func() {
		defer close(submissionDone)
		p.addWork(snapshots, pool)
	}()
	go pool.Start(data)

	details := make(map[string]*domain.Details)
	cancellation := p.owned.ctx.Done()
	aborted := false
	stop := func(err error) {
		if !aborted {
			aborted = true
			p.errors.Add(err)
			pool.Stop()
			p.owned.cancel()
		}
		// A permanently ready cancellation channel must not spin while native
		// workers are still returning. Their actual result channel is drained.
		cancellation = nil
	}
	for {
		select {
		case <-cancellation:
			stop(p.owned.ctx.Err())
		case raw, open := <-pool.Results():
			if !open {
				<-submissionDone
				if p.nativeMapping != nil {
					p.nativeMappingBatchesDrained++
				}
				if !aborted && p.owned.ctx.Err() != nil {
					stop(p.owned.ctx.Err())
				}
				if aborted {
					return nil
				}
				return details
			}
			result := raw.(*creator.Result)
			if result.Err != nil {
				p.errors.Add(result.Err)
				// The owned route always retires on a failed native task. Partial
				// effects remain retained; it never claims atomic rollback.
				stop(fmt.Errorf("owned native object creation failed: %w", result.Err))
			}
			if !aborted {
				if err := p.request.Progress.TryStep(1); err != nil {
					stop(fmt.Errorf("%w: %s", common.ErrCancel, err.Error()))
				}
			}
			details[result.NewID] = result.Details
		}
	}
}
