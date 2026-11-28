package object

import (
	"context"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
)

func definitionOperationValid(ch crdt.Change, entry *migrationintent.Prepared) bool {
	if entry == nil || !migrationintent.IsDefinition(entry.Kind) || ch.NativeDefinitionPolicy != entry.Kind || ch.NativeObjectPolicy || len(ch.Records) == 0 || len(ch.Records) > 2048 {
		return false
	}
	if entry.Kind != migrationintent.PartDefinition && len(ch.Records) != 1 {
		return false
	}
	for _, r := range ch.Records {
		if !r.Upsert {
			return false
		}
	}
	return true
}

func (o *Object) PrepareMigrationDefinition(ctx context.Context, ch crdt.Change, entry *migrationintent.Prepared, journal *migrationintent.Store) (*migrationintent.Prepared, error) {
	if journal == nil || !definitionOperationValid(ch, entry) {
		return nil, crdt.ErrValidation
	}
	op := &preparedOperation{entry: entry, journal: journal, definition: true}
	_, err := o.localWriteIf(context.WithValue(ctx, migrationContextKey{}, op), ch, nil, nil, true)
	if err != nil {
		return nil, err
	}
	if op.entry.ChangeID == "" || len(op.entry.Raw) == 0 {
		return nil, migrationintent.ErrCorrupt
	}
	return op.entry, nil
}
func (o *Object) CommitMigrationDefinition(ctx context.Context, ch crdt.Change, entry *migrationintent.Prepared) (WriteResult, string, error) {
	if !definitionOperationValid(ch, entry) {
		return WriteResult{}, "", crdt.ErrValidation
	}
	op := &preparedOperation{entry: entry, commit: true, definition: true}
	ch.Timestamp = entry.Timestamp
	result, err := o.localWriteIf(context.WithValue(ctx, migrationContextKey{}, op), ch, nil, nil, true)
	return result, op.outcome, err
}
func (o *Object) MigrationDefinitionStatus(ctx context.Context, entry *migrationintent.Prepared) (WriteResult, string, error) {
	if entry == nil || !migrationintent.IsDefinition(entry.Kind) {
		return WriteResult{}, "", crdt.ErrValidation
	}
	return o.migrationStatus(ctx, entry, true)
}
