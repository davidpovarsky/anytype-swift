package readonlyfixer

import (
 torah "github.com/anyproto/anytype-heart/core/pinkha/torah"
 "github.com/anyproto/anytype-heart/pkg/lib/bundle"
 "github.com/anyproto/anytype-heart/pkg/lib/database"
 "github.com/anyproto/anytype-heart/pkg/lib/pb/model"
)

// Exclude only genuine fixed-key native definitions. Display-name collisions,
// user properties and ordinary Tag/Status maintenance keep original semantics.
// This does not repair old data or introduce any new migration/backfill.
func preserveNativeDerivedDefinitions(records []database.Record, err error) ([]database.Record, error) {
 if err != nil { return records, err }
 kept := records[:0]
 for _, record := range records {
  details := record.Details
  key := details.GetString(bundle.RelationKeyRelationKey)
  if torah.IsProperty(key) && details.GetString(bundle.RelationKeySourceObject) == "_br"+key &&
   details.GetInt64(bundle.RelationKeyRelationFormat) == int64(model.RelationFormat_tag) {
   continue
  }
  kept = append(kept, record)
 }
 return kept, nil
}
