package torahindex

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"strings"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

// RecoveryStats describes local work, not a synced or independently ready index.
type RecoveryStats struct {
	Scanned    int
	Reused     int
	Recomputed int
	Complete   bool
}

func (i *Index) LastRecoveryStats() RecoveryStats {
	if result := i.recovery.Load(); result != nil {
		return *result
	}
	return RecoveryStats{}
}

var cacheInputKeys = func() []domain.RelationKey {
	keys := []domain.RelationKey{bundle.RelationKeyId, bundle.RelationKeySpaceId,
		bundle.RelationKeyType, bundle.RelationKeyTargetObjectType,
		bundle.RelationKeyIsDeleted, bundle.RelationKeyIsArchived}
	for _, key := range torah.LocalKeys() {
		if key != torah.CacheIntegrityKey {
			keys = append(keys, domain.RelationKey(key))
		}
	}
	return keys
}()

// The proof covers BOTH the canonical input and every cached output, plus the
// manifest generation and eligibility inputs. Trusting only the canonical hash
// would retain forged/stale arrays left by an older, unadapted client. This is a
// disposable local cache check, not an authentication or transport signature.
func cacheProof(binding torah.Binding, details *domain.Details) string {
	keys := append(append([]domain.RelationKey(nil), cacheInputKeys...), domain.RelationKey(binding.CanonicalKey))
	data, err := json.Marshal(details.CopyOnlyKeys(keys...).ToProto())
	if err != nil {
		return ""
	}
	hash := sha256.New()
	hash.Write([]byte("pinkha-torah-cache-v1\x00" + binding.Generation + "\x00" + binding.CanonicalKey + "\x00"))
	hash.Write(data)
	// Preserve byte identity even for malformed UTF-8 that JSON encoding would
	// otherwise replace. Such payloads must remain explicit errors.
	hash.Write([]byte{0})
	hash.Write([]byte(details.GetString(domain.RelationKey(binding.CanonicalKey))))
	return hex.EncodeToString(hash.Sum(nil))
}

func reusableCache(binding torah.Binding, details *domain.Details) bool {
	stored := details.GetString(domain.RelationKey(torah.CacheIntegrityKey))
	return stored != "" && stored == cacheProof(binding, details)
}

func sealCache(binding torah.Binding, details *domain.Details) {
	if !isManifest(details) && !details.Has(domain.RelationKey(torah.CanonicalKeyKey)) {
		return
	}
	if proof := cacheProof(binding, details); proof != "" {
		details.SetString(domain.RelationKey(torah.CacheIntegrityKey), proof)
	}
}

// Collect only cloned IDs, without decoding/copying each canonical payload in
// this first pass. The cursor is closed before any row changes in the same tx.
func (i *Index) objectIDs(ctx context.Context) ([]string, error) {
	iterator, err := i.objects.Find(nil).Iter(ctx)
	if err != nil {
		return nil, err
	}
	defer iterator.Close()
	var ids []string
	for iterator.Next() {
		document, err := iterator.Doc()
		if err != nil {
			return nil, err
		}
		ids = append(ids, strings.Clone(document.Value().GetString("id")))
	}
	return ids, iterator.Err()
}
