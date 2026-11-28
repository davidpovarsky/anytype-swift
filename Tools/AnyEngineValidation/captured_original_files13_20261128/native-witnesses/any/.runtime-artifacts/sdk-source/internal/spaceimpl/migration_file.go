package spaceimpl

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"slices"

	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync-sdk/space"
)

var _ space.PreparedFileService = (*filesAPI)(nil)

func fullFileReceipt(e *migrationintent.File, stage, outcome string) space.MigrationFileReceipt {
	return space.MigrationFileReceipt{MigrationReceipt: receipt(&e.Prepared, stage, outcome),
		OwnerObjectID: e.OwnerObjectID, FileID: e.RecordIDs[0], ContentSHA256: e.ContentSHA256,
		Size: e.Size, RootCID: e.Staged.RootCID, LocalFileComplete: stage == "complete" && outcome == "committed"}
}

func (f *filesAPI) preparedFileResult(ctx context.Context, e *migrationintent.File, stage, outcome string) (space.MigrationFileReceipt, error) {
	if outcome == "committed" {
		complete, err := f.s.parent.files.MigrationFileAdopted(ctx, f.s.id, e.RecordIDs[0], e.Staged)
		if err != nil {
			return fullFileReceipt(e, stage, outcome), err
		}
		if complete {
			stage = "complete"
		}
	}
	return fullFileReceipt(e, stage, outcome), nil
}

func (f *filesAPI) PrepareMigrationFile(ctx context.Context, input space.MigrationInput, requested space.MigrationFileSpec, body io.Reader) (space.MigrationFileReceipt, error) {
	spec := migrationintent.FileSpec{OwnerObjectID: requested.OwnerObjectID, Name: requested.Name,
		Mime: requested.Mime, Size: requested.Size, ContentSHA256: requested.ContentSHA256}
	if err := spec.Validate(); err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if input.Contract != migrationintent.Contract || input.SpecSHA256 != migrationintent.Digest(input.SourceSpec) {
		return space.MigrationFileReceipt{}, migrationintent.ErrScope
	}
	files := f.s.parent.files
	if files == nil {
		return space.MigrationFileReceipt{}, errors.New("prepared file: files not configured")
	}
	// Refuse a foreign/stopped account, revoked writer or deleted owner before
	// reading any caller bytes. Native preparation repeats the same fences.
	if err := f.s.writeGate(ctx); err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if err := f.s.store.CheckMigrationWriter(ctx); err != nil {
		return space.MigrationFileReceipt{}, err
	}
	owner, err := f.s.store.TreeEntry(ctx, spec.OwnerObjectID)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if !owner.Present || owner.Deleted || owner.Derived {
		return space.MigrationFileReceipt{}, migrationintent.ErrObsolete
	}
	unlock := f.s.store.LockMigration()
	defer unlock()
	journal, err := f.s.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	id := journal.Identity()
	binding := migrationintent.Binding{StoreID: input.StoreID, AccountID: id.AccountID, SpaceID: id.SpaceID,
		PlanID: input.PlanID, PlanSHA256: input.PlanSHA256, IntentID: input.IntentID, SourceKey: input.SourceKey}
	nativeSpec, err := json.Marshal(spec)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	fp, err := journal.FileFingerprint(binding, nativeSpec, input.SourceSpec)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if old, err := journal.LoadFile(ctx, input.IntentID); err == nil {
		if old.Binding != binding || old.Fingerprint != fp {
			return space.MigrationFileReceipt{}, migrationintent.ErrCollision
		}
		stage, outcome, err := f.s.store.MigrationFileState(ctx, old, false)
		if err != nil {
			return fullFileReceipt(old, stage, outcome), err
		}
		return f.preparedFileResult(ctx, old, stage, outcome)
	} else if !errors.Is(err, migrationintent.ErrNotFound) {
		return space.MigrationFileReceipt{}, err
	}
	draft, err := journal.ReserveFileDraft(ctx, migrationintent.Prepared{Binding: binding, Fingerprint: fp,
		Spec: nativeSpec, SourceSpec: slices.Clone(input.SourceSpec), SpecSHA256: input.SpecSHA256})
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	staged, err := files.StageReservedMigrationFile(ctx, f.s.id, binding.IntentID, fp, spec.Size, spec.ContentSHA256, body, draft.Key)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	e := &migrationintent.File{Prepared: draft.Prepared, Staged: staged}
	e.Stage = "file"
	e, err = f.s.store.PrepareMigrationFile(ctx, journal, e, spec)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	stage, outcome, err := f.s.store.MigrationFileState(ctx, e, false)
	if err != nil {
		return fullFileReceipt(e, stage, outcome), err
	}
	return f.preparedFileResult(ctx, e, stage, outcome)
}

func (f *filesAPI) MigrationFileStatus(ctx context.Context, intentID string) (space.MigrationFileReceipt, error) {
	if f.s.parent.files == nil {
		return space.MigrationFileReceipt{}, errors.New("prepared file: files not configured")
	}
	unlock := f.s.store.LockMigration()
	defer unlock()
	journal, err := f.s.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	e, err := journal.LoadFile(ctx, intentID)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	stage, outcome, err := f.s.store.MigrationFileState(ctx, e, false)
	if err != nil {
		return fullFileReceipt(e, stage, outcome), err
	}
	return f.preparedFileResult(ctx, e, stage, outcome)
}

func (f *filesAPI) CommitMigrationFile(ctx context.Context, input space.MigrationCommit) (space.MigrationFileReceipt, error) {
	files := f.s.parent.files
	if files == nil {
		return space.MigrationFileReceipt{}, errors.New("prepared file: files not configured")
	}
	unlock := f.s.store.LockMigration()
	defer unlock()
	journal, err := f.s.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	e, err := journal.LoadFile(ctx, input.IntentID)
	if err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if input.Contract != migrationintent.Contract || input.StoreID != e.Binding.StoreID || input.PlanID != e.Binding.PlanID || input.PlanSHA256 != e.Binding.PlanSHA256 || input.Fingerprint != e.Fingerprint {
		return space.MigrationFileReceipt{}, migrationintent.ErrCollision
	}
	previousStage, previousOutcome, err := f.s.store.MigrationFileState(ctx, e, false)
	if err != nil {
		return fullFileReceipt(e, previousStage, previousOutcome), err
	}
	// A deleted/modified original row stays terminal even if its old bytes
	// have been purged. Reconciliation must never recreate those bytes/rows.
	if previousOutcome != "prepared" && previousOutcome != "committed" {
		return fullFileReceipt(e, previousStage, previousOutcome), nil
	}
	if err = journal.EnsureDurable(ctx); err != nil {
		return space.MigrationFileReceipt{}, err
	}
	if err = files.VerifyMigrationFile(ctx, f.s.id, e.Staged); err != nil {
		return space.MigrationFileReceipt{}, err
	}
	stage, outcome, err := f.s.store.MigrationFileState(ctx, e, true)
	if err != nil {
		return fullFileReceipt(e, stage, outcome), err
	}
	if outcome == "committed" {
		err = f.s.store.AdoptMigrationFile(ctx, e, func() error {
			return files.AdoptMigrationFile(ctx, f.s.id, e.OwnerObjectID, e.RecordIDs[0], e.Staged)
		})
		if err != nil {
			return fullFileReceipt(e, stage, outcome), err
		}
	}
	return f.preparedFileResult(ctx, e, stage, outcome)
}
