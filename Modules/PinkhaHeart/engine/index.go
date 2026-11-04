// Package torahindex maintains local derived fields in Heart's existing native
// Space collection. It never opens a second database or writes synced blocks.
package torahindex

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

type Writer func(context.Context, string, *domain.Details) error
type BeginWrite func(context.Context) (anystore.WriteTx, error)

// All state is owned by one Space store. The caller supplies Heart's notifying
// transaction so subscriptions see the canonical and derived values together,
// only after the root transaction commits, including during rebuild/recovery.
type Index struct {
	space     string
	objects   anystore.Collection
	begin     BeginWrite
	write     Writer
	manifests sync.Map
	active    atomic.Bool
}

func New(space string, objects anystore.Collection, begin BeginWrite, write Writer) *Index {
	return &Index{space: space, objects: objects, begin: begin, write: write}
}

func (i *Index) Recover(ctx context.Context) error {
	for _, key := range []string{torah.SourcesKey, torah.TopicsKey, torah.WordsKey} {
		if err := i.objects.EnsureIndex(ctx, anystore.IndexInfo{Name: key, Fields: []string{key}, Sparse: true}); err != nil {
			return fmt.Errorf("Torah membership index %s: %w", key, err)
		}
	}
	tx, err := i.begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if err = i.rows(tx.Context(), manifestFilter(), func(d *domain.Details) error { i.rememberManifest(d); return nil }); err != nil {
		return err
	}
	if err = i.rebuild(tx.Context()); err != nil {
		return err
	}
	return tx.Commit()
}

// Update is the production ObjectStore write boundary. Incoming derived values
// are discarded, even when an older client sends them, then rebuilt from the
// original canonical payload. Projection errors fail closed for just that row.
func (i *Index) Update(ctx context.Context, id string, details *domain.Details) error {
	if details == nil || details.Len() == 0 {
		return errors.New("empty details")
	}
	// Preserve the original native method's documented ID assignment, including
	// callers that retain this Details pointer after the write.
	details.SetString(bundle.RelationKeyId, id)
	i.rememberManifest(details.Copy().SetString(bundle.RelationKeyId, id))
	// No manifest has ever been observed in this Space. Preserve the original
	// cheap write path; ordinary Anytype edits do not scan a Pinkha-free Space.
	if !i.active.Load() {
		return i.write(ctx, id, clear(details))
	}
	tx, err := i.begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	ctx = tx.Context()
	before, err := i.read(ctx, id)
	if err != nil && !errors.Is(err, anystore.ErrDocNotFound) {
		return err
	}
	clean := clear(details)
	clean.SetString(bundle.RelationKeyId, id)
	source := source{index: i}
	binding, bindingErr := torah.ResolveBinding(ctx, source, i.space)
	// Changes to a manifest or its canonical property invalidate every row in
	// this Space, in the same transaction as the triggering native write.
	rebind := isManifest(clean) || isManifest(before) || source.isCanonicalCandidate(ctx, id)
	if bindingErr == nil && clean.GetString(bundle.RelationKeyRelationKey) == binding.CanonicalKey {
		rebind = true
	}
	if bindingErr == nil && before != nil && before.GetString(bundle.RelationKeyRelationKey) == binding.CanonicalKey {
		rebind = true
	}
	if rebind {
		if err = i.write(ctx, id, clean); err != nil {
			return err
		}
		if err = i.rebuild(ctx); err != nil {
			return err
		}
	} else {
		if bindingErr == nil {
			i.project(binding, clean)
		}
		if err = i.write(ctx, id, clean); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (i *Index) rememberManifest(d *domain.Details) {
	if isManifest(d) {
		i.manifests.Store(d.GetString(bundle.RelationKeyId), struct{}{})
		i.active.Store(true)
	}
}

func manifestFilter() map[string]any {
	return map[string]any{"$or": []any{
		map[string]any{string(bundle.RelationKeyUniqueKey): torah.ManifestUniqueKey},
		map[string]any{string(bundle.RelationKeyName): torah.ManifestUniqueKey},
	}}
}

// Delete invalidates bindings before deleting the triggering row. The caller
// uses the same notifying tx for the physical deletion and commit.
func (i *Index) Delete(ctx context.Context, ids []string, remove func(context.Context) error) error {
	if !i.active.Load() {
		return remove(ctx)
	}
	tx, err := i.begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	rebind := false
	for _, id := range ids {
		_, knownManifest := i.manifests.Load(id)
		rebind = rebind || knownManifest || (source{index: i}).isCanonicalCandidate(tx.Context(), id)
	}
	if err = remove(tx.Context()); err != nil {
		return err
	}
	if rebind {
		if err = i.rebuild(tx.Context()); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (i *Index) Modify(ctx context.Context, id string, proc func(*domain.Details) (*domain.Details, bool, error), upsert bool,
	nativeModify func(context.Context, string, func(*domain.Details) (*domain.Details, bool, error), bool) error) error {
	if proc == nil {
		return nil
	}
	tx, err := i.begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	previous, err := i.read(tx.Context(), id)
	if errors.Is(err, anystore.ErrDocNotFound) {
		if !upsert {
			return nil
		}
	} else if err != nil {
		return err
	}
	// Preserve native Modify's complete contract, including nil/id-only results,
	// skipped missing rows, modifier failures and native notifications. Both
	// writes remain invisible until the same root notifying transaction commits.
	rebind := isManifest(previous) || (source{index: i}).isCanonicalCandidate(tx.Context(), id)
	if err = nativeModify(tx.Context(), id, proc, upsert); err != nil {
		return err
	}
	d, err := i.read(tx.Context(), id)
	if errors.Is(err, anystore.ErrDocNotFound) {
		return tx.Commit()
	}
	if err != nil {
		return err
	}
	i.rememberManifest(d)
	if rebind || isManifest(d) {
		if err = i.rebuild(tx.Context()); err != nil {
			return err
		}
	} else if d.Len() > 1 {
		if err = i.Update(tx.Context(), id, d); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func clear(details *domain.Details) *domain.Details {
	clean := details.Copy()
	for _, key := range torah.LocalKeys() {
		clean.Delete(domain.RelationKey(key))
	}
	return clean
}

func isManifest(d *domain.Details) bool {
	return d != nil && (d.GetString(bundle.RelationKeyUniqueKey) == torah.ManifestUniqueKey || d.GetString(bundle.RelationKeyName) == torah.ManifestUniqueKey)
}

func (i *Index) read(ctx context.Context, id string) (*domain.Details, error) {
	doc, err := i.objects.FindId(ctx, id)
	if err != nil {
		return nil, err
	}
	return domain.NewDetailsFromAnyEnc(doc.Value())
}

func (i *Index) rows(ctx context.Context, filter any, visit func(*domain.Details) error) error {
	iter, err := i.objects.Find(filter).Iter(ctx)
	if err != nil {
		return err
	}
	defer iter.Close()
	for iter.Next() {
		doc, e := iter.Doc()
		if e != nil {
			return e
		}
		d, e := domain.NewDetailsFromAnyEnc(doc.Value())
		if e != nil {
			return e
		}
		if e = visit(d); e != nil {
			return e
		}
	}
	return iter.Err()
}

func (i *Index) rebuild(ctx context.Context) error {
	binding, bindingErr := torah.ResolveBinding(ctx, source{index: i}, i.space)
	// Keep only object IDs while traversing. Updating a live SQL cursor can skip
	// or revisit rows. The payload stays in the original collection and tx.
	var ids []string
	if err := i.rows(ctx, nil, func(d *domain.Details) error { ids = append(ids, d.GetString(bundle.RelationKeyId)); return nil }); err != nil {
		return err
	}
	for _, id := range ids {
		original, err := i.read(ctx, id)
		if err != nil {
			return err
		}
		d := clear(original)
		if bindingErr == nil {
			i.project(binding, d)
			if isManifest(d) {
				d.SetInt64(domain.RelationKey(torah.VersionKey), torah.Version)
				d.SetString(domain.RelationKey(torah.CanonicalHashKey), binding.Generation)
			}
		}
		if !d.Equal(original) {
			if err = i.write(ctx, id, d); err != nil {
				return err
			}
		}
	}
	return nil
}

func (i *Index) project(binding torah.Binding, d *domain.Details) {
	types := d.GetStringList(bundle.RelationKeyType)
	if len(types) != 1 {
		return
	}
	space := d.GetString(bundle.RelationKeySpaceId)
	// The collection itself is per Space; a conflicting explicit ID is rejected.
	if space != "" && space != i.space {
		return
	}
	p, err := torah.Project(binding, torah.Input{
		SpaceID: i.space, ObjectID: d.GetString(bundle.RelationKeyId), TypeID: types[0],
		IsTemplate: d.Has(bundle.RelationKeyTargetObjectType),
		IsDeleted:  d.GetBool(bundle.RelationKeyIsDeleted), IsArchived: d.GetBool(bundle.RelationKeyIsArchived),
		Raw: []byte(d.GetString(domain.RelationKey(binding.CanonicalKey))),
	})
	if err != nil {
		if errors.Is(err, torah.ErrMalformed) || errors.Is(err, torah.ErrUnsupported) {
			d.SetBool(domain.RelationKey(torah.ReadyKey), false)
			d.SetInt64(domain.RelationKey(torah.VersionKey), torah.Version)
			status := "MALFORMED"
			if errors.Is(err, torah.ErrUnsupported) {
				status = "UNSUPPORTED"
			}
			d.SetString(domain.RelationKey(torah.StatusKey), status)
		}
		return
	}
	for key, values := range map[string][]string{torah.SourcesKey: p.Sources, torah.TopicsKey: p.Topics, torah.WordsKey: p.Words} {
		if len(values) > 0 {
			d.SetStringList(domain.RelationKey(key), values)
		}
	}
	labels, _ := json.Marshal(p.Labels)
	d.SetString(domain.RelationKey(torah.LabelsKey), string(labels))
	d.SetBool(domain.RelationKey(torah.ReadyKey), true)
	d.SetString(domain.RelationKey(torah.StatusKey), "READY")
	d.SetInt64(domain.RelationKey(torah.VersionKey), torah.Version)
	d.SetString(domain.RelationKey(torah.CanonicalHashKey), p.CanonicalSHA256)
}

type source struct{ index *Index }

func (s source) isCanonicalCandidate(ctx context.Context, id string) bool {
	candidates, err := s.Manifests(ctx, s.index.space)
	if err != nil {
		return false
	}
	for _, candidate := range candidates {
		var m struct {
			CanonicalID string `json:"documentAssociationsPropertyId"`
		}
		if json.Unmarshal(candidate.Raw, &m) == nil && m.CanonicalID == id {
			return true
		}
	}
	return false
}

func (s source) Manifests(ctx context.Context, space string) ([]torah.ManifestCandidate, error) {
	if space != s.index.space {
		return nil, torah.ErrBinding
	}
	var found []torah.ManifestCandidate
	var readErr error
	// Cache only candidate IDs, never a binding or payload. Read each candidate
	// from the caller's actual transaction, so rollback/rebind cannot leave stale
	// membership or leak another Space. A rolled-back new ID is harmless.
	s.index.manifests.Range(func(id, _ any) bool {
		d, err := s.index.read(ctx, id.(string))
		if errors.Is(err, anystore.ErrDocNotFound) {
			return true
		}
		if err != nil {
			readErr = err
			return false
		}
		if isManifest(d) && !d.GetBool(bundle.RelationKeyIsDeleted) && !d.GetBool(bundle.RelationKeyIsArchived) {
			found = append(found, torah.ManifestCandidate{ObjectID: d.GetString(bundle.RelationKeyId), Raw: []byte(d.GetString(bundle.RelationKeyDescription))})
		}
		return true
	})
	return found, readErr
}
func (s source) CanonicalProperty(ctx context.Context, space, key string) (torah.PropertyDescriptor, error) {
	if space != s.index.space {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	manifests, err := s.Manifests(ctx, space)
	if err != nil || len(manifests) != 1 {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	var m struct {
		CanonicalID string `json:"documentAssociationsPropertyId"`
	}
	if json.Unmarshal(manifests[0].Raw, &m) != nil {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	d, err := s.index.read(ctx, m.CanonicalID)
	if err != nil {
		return torah.PropertyDescriptor{}, err
	}
	if !d.Has(bundle.RelationKeyRelationFormat) || d.GetInt64(bundle.RelationKeyLayout) != int64(model.ObjectType_relation) {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	if d.GetBool(bundle.RelationKeyIsDeleted) || d.GetBool(bundle.RelationKeyIsArchived) {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	if value := d.GetString(bundle.RelationKeySpaceId); value != "" && value != space {
		return torah.PropertyDescriptor{}, torah.ErrBinding
	}
	return torah.PropertyDescriptor{ID: d.GetString(bundle.RelationKeyId), Key: d.GetString(bundle.RelationKeyRelationKey), Format: int(d.GetInt64(bundle.RelationKeyRelationFormat))}, nil
}
