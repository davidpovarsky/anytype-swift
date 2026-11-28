package spaceimpl

import (
	"context"
	"encoding/json"
	"errors"
	"maps"
	"slices"

	"github.com/anyproto/any-store/v2/anyenc"
	"github.com/anyproto/any-sync-sdk/internal/commitguard"
	"github.com/anyproto/any-sync-sdk/internal/crdt"
	"github.com/anyproto/any-sync-sdk/internal/migrationintent"
	"github.com/anyproto/any-sync-sdk/internal/properties"
	collectiontype "github.com/anyproto/any-sync-sdk/internal/types/collection"
	typetype "github.com/anyproto/any-sync-sdk/internal/types/type"
	"github.com/anyproto/any-sync-sdk/space"
)

var _ space.PreparedDefinitionService = (*objectService)(nil)

func (o *objectService) MigrationDefinitionCapabilities(ctx context.Context) (space.MigrationDefinitionCapabilities, error) {
	journal, err := o.parent.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationDefinitionCapabilities{}, err
	}
	id := journal.Identity()
	return space.MigrationDefinitionCapabilities{Contract: migrationintent.DefinitionContract, StoreID: id.StoreID, AccountID: id.AccountID, SpaceID: id.SpaceID, TypeDefinition: 1, CollectionDefinition: 1, PropertyDefinition: 1, PartDefinition: 1, NetworkVerified: false}, nil
}
func definitionReceipt(e *migrationintent.Prepared, stage, outcome string) space.MigrationReceipt {
	r := receipt(e, stage, outcome)
	r.Contract = migrationintent.DefinitionContract
	return r
}
func validDefinitionShape(s space.MigrationDefinitionSpec) bool {
	switch s.Kind {
	case migrationintent.TypeDefinition:
		return s.Type != nil && s.Collection == nil && s.Property == nil && s.Part == nil && s.OwnerObjectID == ""
	case migrationintent.CollectionDefinition:
		return s.Collection != nil && s.Type == nil && s.Property == nil && s.Part == nil && s.OwnerObjectID == ""
	case migrationintent.PropertyDefinition:
		return s.Property != nil && s.Type == nil && s.Collection == nil && s.Part == nil && s.OwnerObjectID != "" && len(s.OwnerObjectID) <= 256
	case migrationintent.PartDefinition:
		return s.Part != nil && s.Type == nil && s.Collection == nil && s.Property == nil && s.OwnerObjectID != "" && len(s.OwnerObjectID) <= 256
	}
	return false
}

func definitionSpec(e *migrationintent.Prepared) (space.MigrationDefinitionSpec, error) {
	var spec space.MigrationDefinitionSpec
	// Exact-number validation happened before durable reservation. Standard
	// JSON normalization gives creation and restart the same map/scalar forms.
	if json.Unmarshal(e.Spec, &spec) != nil || !validDefinitionShape(spec) || spec.Kind != e.Kind {
		return spec, migrationintent.ErrCorrupt
	}
	return spec, nil
}
func definitionEntry(j *migrationintent.Store, input space.MigrationInput, spec space.MigrationDefinitionSpec) (*migrationintent.Prepared, error) {
	if input.Contract != migrationintent.DefinitionContract || input.SpecSHA256 != migrationintent.Digest(input.SourceSpec) || !validDefinitionShape(spec) {
		return nil, migrationintent.ErrScope
	}
	id := j.Identity()
	b := migrationintent.Binding{StoreID: input.StoreID, AccountID: id.AccountID, SpaceID: id.SpaceID, PlanID: input.PlanID, PlanSHA256: input.PlanSHA256, IntentID: input.IntentID, SourceKey: input.SourceKey}
	raw, err := json.Marshal(spec)
	if err != nil {
		return nil, err
	}
	fp, err := j.DefinitionFingerprint(b, spec.Kind, raw, input.SourceSpec)
	if err != nil {
		return nil, err
	}
	stage := migrationintent.DefinitionRoot
	if spec.Kind == migrationintent.PropertyDefinition {
		stage = migrationintent.DefinitionProperty
	} else if spec.Kind == migrationintent.PartDefinition {
		stage = migrationintent.DefinitionPart
	}
	return &migrationintent.Prepared{Binding: b, Kind: spec.Kind, Stage: stage, Spec: raw, SourceSpec: slices.Clone(input.SourceSpec), SpecSHA256: input.SpecSHA256, Fingerprint: fp}, nil
}

func (o *objectService) definitionChange(ctx context.Context, id string, spec space.MigrationDefinitionSpec) (crdt.Change, error) {
	if !validDefinitionShape(spec) {
		return crdt.Change{}, crdt.ErrValidation
	}
	if spec.Kind == migrationintent.PartDefinition {
		return o.definitionPartChange(ctx, spec, nil)
	}
	a := &anyenc.Arena{}
	var payload *anyenc.Value
	dataset := properties.Dataset
	if spec.Kind == migrationintent.PropertyDefinition {
		draft := spec.Property
		if err := validatePropertyDraft(draft); err != nil {
			return crdt.Change{}, err
		}
		// The current native ordinary property constructor has no recursive
		// child-definition writer. Refuse these inputs instead of dropping them.
		if draft.Items != nil || len(draft.Properties) > 0 || len(draft.Required) > 0 {
			return crdt.Change{}, crdt.ErrValidation
		}
		var err error
		payload, err = propertyDefPayload(a, draft)
		if err != nil {
			return crdt.Change{}, err
		}
		if len(draft.Meta) > 0 {
			meta := a.NewObject()
			for _, k := range slices.Sorted(maps.Keys(draft.Meta)) {
				meta.Set(k, a.NewString(draft.Meta[k]))
			}
			payload.Set(typetype.FieldMeta, meta)
		}
		dataset = typetype.DatasetPropertyDefs
		id = ""
	} else {
		var name, description, icon, xkey, namespace, marker string
		var hidden bool
		var meta, layout map[string]any
		if spec.Kind == migrationintent.TypeDefinition {
			p := spec.Type
			name, description, icon, xkey, hidden, meta, layout = p.Name, p.Description, p.IconCID, p.XKey, p.Hidden, p.Meta, p.Layout
			namespace, marker = typetype.TypeId, typetype.MetaTypeMarker
		} else {
			p := spec.Collection
			name, description, icon, xkey, hidden, meta = p.Name, p.Description, p.IconCID, p.XKey, p.Hidden, p.Meta
			namespace, marker = collectiontype.TypeId, collectiontype.MetaMarker
		}
		payload = a.NewObject()
		for _, p := range [][2]string{{"any.name", name}, {"any.description", description}, {"any.icon", icon}, {namespace + "." + typetype.FieldXKeyProp, xkey}} {
			if p[1] != "" {
				payload.Set(p[0], a.NewString(p[1]))
			}
		}
		if len(layout) > 0 {
			v, err := encodeXFormat(a, layout)
			if err != nil {
				return crdt.Change{}, err
			}
			payload.Set(namespace+"."+typetype.FieldLayoutProp, v)
		}
		if hidden {
			payload.Set(namespace+"."+typetype.FieldHiddenProp, a.NewTrue())
		}
		for _, k := range slices.Sorted(maps.Keys(meta)) {
			v, err := typeMetaValue(a, k, meta[k])
			if err != nil {
				return crdt.Change{}, err
			}
			if v != nil {
				payload.Set(namespace+"."+typetype.FieldMetaProp+"."+k, v)
			}
		}
		payload.Set("any.type", a.NewString(marker))
	}
	version, err := o.parent.store.DataVersion(dataset)
	if err != nil {
		return crdt.Change{}, err
	}
	return crdt.Change{Dataset: dataset, DataVersion: version, NativeDefinitionPolicy: spec.Kind, Records: []crdt.RecordChange{{Id: id, Upsert: true, Ops: []crdt.Op{{Type: crdt.OpSet, Payload: payload}}}}}, nil
}

func (o *objectService) PrepareMigrationDefinition(ctx context.Context, input space.MigrationInput, spec space.MigrationDefinitionSpec) (space.MigrationReceipt, error) {
	unlock := o.parent.store.LockMigration()
	defer unlock()
	journal, err := o.parent.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	entry, err := definitionEntry(journal, input, spec)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if old, e := journal.LoadDefinition(ctx, input.IntentID, entry.Stage); e == nil {
		if old.Binding != entry.Binding || old.Fingerprint != entry.Fingerprint {
			return space.MigrationReceipt{}, migrationintent.ErrCollision
		}
		return o.definitionStatus(ctx, journal, old)
	} else if !errors.Is(e, migrationintent.ErrNotFound) {
		return space.MigrationReceipt{}, e
	}
	normalized, err := definitionSpec(entry)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	change, err := o.definitionChange(ctx, "", normalized)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if entry.Stage == migrationintent.DefinitionRoot {
		entry, err = o.parent.store.PrepareMigrationDefinitionRoot(ctx, journal, entry)
	} else {
		obj, e := o.parent.store.Get(ctx, spec.OwnerObjectID)
		if e != nil {
			return space.MigrationReceipt{}, e
		}
		entry, err = obj.PrepareMigrationDefinition(ctx, change, entry, journal)
	}
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	return o.definitionStatus(ctx, journal, entry)
}
func loadDefinition(ctx context.Context, journal *migrationintent.Store, intent string) (*migrationintent.Prepared, error) {
	e, err := journal.LoadDefinition(ctx, intent, migrationintent.DefinitionRoot)
	if errors.Is(err, migrationintent.ErrNotFound) {
		e, err = journal.LoadDefinition(ctx, intent, migrationintent.DefinitionProperty)
		if errors.Is(err, migrationintent.ErrNotFound) {
			return journal.LoadDefinition(ctx, intent, migrationintent.DefinitionPart)
		}
	}
	return e, err
}
func (o *objectService) MigrationDefinitionStatus(ctx context.Context, intent string) (space.MigrationReceipt, error) {
	unlock := o.parent.store.LockMigration()
	defer unlock()
	journal, err := o.parent.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	e, err := loadDefinition(ctx, journal, intent)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	return o.definitionStatus(ctx, journal, e)
}
func (o *objectService) definitionStatus(ctx context.Context, journal *migrationintent.Store, e *migrationintent.Prepared) (space.MigrationReceipt, error) {
	stage := "definition-property-prepared"
	if e.Stage == migrationintent.DefinitionPart {
		stage = "definition-part-prepared"
	}
	if e.Stage == migrationintent.DefinitionRoot {
		state, err := o.parent.store.MigrationDefinitionRootState(ctx, e)
		if err != nil {
			return space.MigrationReceipt{}, err
		}
		switch state {
		case "obsolete", "deleted":
			return definitionReceipt(e, "definition-root-prepared", "obsolete"), nil
		case "prepared":
			return definitionReceipt(e, "definition-root-prepared", "prepared"), nil
		}
		bootstrap, err := journal.LoadDefinition(ctx, e.Binding.IntentID, migrationintent.DefinitionBootstrap)
		if errors.Is(err, migrationintent.ErrNotFound) {
			return definitionReceipt(e, "definition-root-committed", "prepared"), nil
		}
		if err != nil {
			return space.MigrationReceipt{}, err
		}
		e = bootstrap
	}
	if e.Stage == migrationintent.DefinitionBootstrap {
		stage = "definition-bootstrap-prepared"
	}
	head, err := o.parent.store.TreeEntry(ctx, e.ObjectID)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if head.Deleted {
		return definitionReceipt(e, stage, "obsolete"), nil
	}
	obj, err := o.parent.store.Get(ctx, e.ObjectID)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	_, outcome, err := obj.MigrationDefinitionStatus(ctx, e)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if outcome == "committed" || outcome == "committed_modified" || outcome == "committed_deleted" {
		stage = "complete"
	}
	return definitionReceipt(e, stage, outcome), nil
}
func (o *objectService) CommitMigrationDefinition(ctx context.Context, input space.MigrationCommit) (space.MigrationReceipt, error) {
	unlock := o.parent.store.LockMigration()
	defer unlock()
	journal, err := o.parent.store.MigrationJournal(ctx)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	e, err := loadDefinition(ctx, journal, input.IntentID)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if input.Contract != migrationintent.DefinitionContract || input.StoreID != e.Binding.StoreID || input.PlanID != e.Binding.PlanID || input.PlanSHA256 != e.Binding.PlanSHA256 || input.Fingerprint != e.Fingerprint {
		return space.MigrationReceipt{}, migrationintent.ErrCollision
	}
	status, err := o.definitionStatus(ctx, journal, e)
	if err != nil || status.Outcome != "prepared" {
		return status, err
	}
	if err = journal.EnsureDurable(ctx); err != nil {
		return space.MigrationReceipt{}, err
	}
	if status.Stage == "definition-root-prepared" {
		err = o.parent.store.CommitMigrationDefinitionRoot(ctx, e)
		if errors.Is(err, migrationintent.ErrObsolete) || errors.Is(err, commitguard.ErrNativeACLChanged) {
			return definitionReceipt(e, status.Stage, "obsolete"), nil
		}
		if err != nil {
			return space.MigrationReceipt{}, err
		}
		return definitionReceipt(e, "definition-root-committed", "prepared"), nil
	}
	spec, err := definitionSpec(e)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	var change crdt.Change
	if spec.Kind == migrationintent.PartDefinition {
		change, err = o.definitionPartChange(ctx, spec, e)
	} else {
		change, err = o.definitionChange(ctx, e.ObjectID, spec)
	}
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	obj, err := o.parent.store.Get(ctx, e.ObjectID)
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	if e.Stage == migrationintent.DefinitionRoot {
		if status.Stage == "definition-root-committed" {
			copy := *e
			copy.Stage, copy.ChangeID, copy.Raw = migrationintent.DefinitionBootstrap, "", nil
			bootstrap, err := obj.PrepareMigrationDefinition(ctx, change, &copy, journal)
			if err != nil {
				return space.MigrationReceipt{}, err
			}
			return definitionReceipt(bootstrap, "definition-bootstrap-prepared", "prepared"), nil
		}
		e, err = journal.LoadDefinition(ctx, e.Binding.IntentID, migrationintent.DefinitionBootstrap)
		if err != nil {
			return space.MigrationReceipt{}, err
		}
	}
	_, outcome, err := obj.CommitMigrationDefinition(ctx, change, e)
	if errors.Is(err, migrationintent.ErrObsolete) || outcome == "obsolete" {
		return definitionReceipt(e, status.Stage, "obsolete"), nil
	}
	if err != nil {
		return space.MigrationReceipt{}, err
	}
	return definitionReceipt(e, "complete", outcome), nil
}
