package application

import (
	"context"
	"errors"
	"testing"
)

// Negative admission controls use an actual empty original Service. They do
// not construct an importer, inject an executor, forge Done or prove runtime.
func TestOwnedAnnotationImportNegativeAdmission(t *testing.T) {
	var secret [32]byte
	secret[0] = 1
	service := &Service{}
	completion, err := service.ImportOwnedAnnotation(context.Background(), "account", []byte("data-only"),
		[32]byte{}, "root", "source-space", "target-space", secret)
	if !errors.Is(err, ErrOwnedImportAdmissionUnavailable) || completion.Registered() || completion.Done() {
		t.Fatal("empty original application admitted an import")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	completion, err = service.ImportOwnedAnnotation(ctx, "account", nil, [32]byte{}, "root", "source-space", "target-space", secret)
	if !errors.Is(err, context.Canceled) || completion.Registered() || completion.Done() {
		t.Fatal("pre-cancelled request acquired admission or synthetic completion")
	}
	service.lock.Lock()
	completion, err = service.ImportOwnedAnnotation(context.Background(), "account", nil, [32]byte{}, "root", "source-space", "target-space", secret)
	service.lock.Unlock()
	if !errors.Is(err, ErrOwnedImportAdmissionUnavailable) || completion.Registered() || completion.Done() {
		t.Fatal("admission did not refuse the actual held original writer lock")
	}
	if len(service.ownedImports.operations) != 0 {
		t.Fatal("negative admission retained an operation or token")
	}
}

func TestOwnedAnnotationCancellationMissIsNotDrain(t *testing.T) {
	service := &Service{}
	var digest, secret [32]byte
	secret[0] = 1
	for i := 0; i < 2; i++ {
		if actual := service.CancelOwnedAnnotationImport("account", "root", "source-space", "target-space", digest, secret); actual != OwnedAnnotationCancelNotObserved {
			t.Fatal("unregistered attempt was acknowledged as cancellation or drain")
		}
	}
	if len(service.ownedImports.operations) != 0 || service.ownedImports.pending || service.ownedImports.retirements != 0 {
		t.Fatal("cancellation-only miss created or retired an owner")
	}
}
