package heartprobe

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"testing"
	"time"

	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pkg/lib/bundle"
	"github.com/anyproto/anytype-heart/pkg/lib/database"
	"github.com/anyproto/anytype-heart/pkg/lib/localstore/objectstore/spaceindex"
	derived "pinkha.local/torah-derived-spike"
)

type trackingTB struct {
	*testing.T
	dirs []string
}

func (t *trackingTB) TempDir() string { dir := t.T.TempDir(); t.dirs = append(t.dirs, dir); return dir }
func (t *trackingTB) bytes() int64 {
	var size int64
	for _, dir := range t.dirs {
		if err := filepath.WalkDir(dir, func(path string, entry fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if entry.IsDir() {
				return nil
			}
			info, err := entry.Info()
			if err == nil {
				size += info.Size()
			}
			return err
		}); err != nil {
			t.Fatal(err)
		}
	}
	return size
}

func TestNativeBenchmarks(t *testing.T) {
	if os.Getenv("PINKHA_NATIVE_BENCH") != "1" {
		t.Skip("explicit synthetic benchmark opt-in required")
	}
	for _, count := range []int{100, 2000, 10000, 50000} {
		t.Run(fmt.Sprint(count), func(t *testing.T) {
			baselineTB, derivedTB := &trackingTB{T: t}, &trackingTB{T: t}
			baseline, derivedStore := spaceindex.NewStoreFixture(baselineTB), spaceindex.NewStoreFixture(derivedTB)
			ctx := context.Background()
			// Two identities per object; half repeated, half unique. This is one
			// measured workload, not an assertion that 10/50-link workloads passed.
			write := func(store spaceindex.Store, withProjection bool) time.Duration {
				started := time.Now()
				for start := 0; start < count; start += 500 {
					tx, err := store.WriteTx(ctx)
					if err != nil {
						t.Fatal(err)
					}
					for n := start; n < start+500 && n < count; n++ {
						id := fmt.Sprintf("doc-%06d", n)
						items := []map[string]string{}
						for _, ref := range []string{fmt.Sprintf("shared-%d", n%10), fmt.Sprintf("unique-%d", n)} {
							items = append(items, map[string]string{"id": ref, "kind": "ref", "role": "context", "providerID": "sefaria", "canonicalKey": ref, "externalID": ref, "labelHe": "מקור בדיקה"})
						}
						raw, err := json.Marshal(map[string]any{"version": 1, "items": items})
						if err != nil {
							t.Fatal(err)
						}
						details := domain.NewDetailsFromMap(map[domain.RelationKey]domain.Value{
							bundle.RelationKeyId: domain.String(id), bundle.RelationKeyName: domain.String("synthetic benchmark"),
							"canonicalFixture": domain.String(string(raw)),
						})
						if withProjection {
							projection, err := derived.Project(derived.Binding{SpaceID: "test-space", CanonicalKey: "canonicalFixture", WritingTypeIDs: [3]string{"chiddush", "article", "research"}, Generation: "bench-1"}, derived.Input{SpaceID: "test-space", ObjectID: id, TypeID: "chiddush", Raw: raw})
							if err != nil {
								t.Fatal(err)
							}
							details.SetStringList(sources, projection.Sources)
							details.SetBool(ready, true)
						}
						if err := store.UpdateObjectDetails(tx.Context(), id, details); err != nil {
							t.Fatal(err)
						}
					}
					if err := tx.Commit(); err != nil {
						t.Fatal(err)
					}
				}
				return time.Since(started)
			}
			baselineDuration, derivedDuration := write(baseline, false), write(derivedStore, true)
			for _, store := range []spaceindex.Store{baseline, derivedStore} {
				total, err := store.CountRaw(&database.Filters{FilterObj: database.FilterExists{Key: bundle.RelationKeyId}})
				if err != nil {
					t.Fatal(err)
				}
				if total != count {
					t.Fatalf("object explosion: expected %d document rows, got %d", count, total)
				}
			}
			filters := &database.Filters{FilterObj: database.FilterIn{Key: sources, Value: []domain.Value{domain.String(derived.Identity(derived.Ref, "sefaria", "shared-1", ""))}}}
			latencies := make([]time.Duration, 100)
			for n := range latencies {
				started := time.Now()
				total, err := derivedStore.CountRaw(filters)
				if err != nil {
					t.Fatal(err)
				}
				if total != count/10 {
					t.Fatalf("count mismatch: %d", total)
				}
				page, err := derivedStore.QueryRaw(filters, 25, 0)
				if err != nil {
					t.Fatal(err)
				}
				if len(page) != min(25, count/10) {
					t.Fatal("page mismatch")
				}
				latencies[n] = time.Since(started)
			}
			sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
			row := map[string]any{"documents": count, "refs_per_doc": 2, "baseline_write_ms": baselineDuration.Milliseconds(), "derived_write_ms": derivedDuration.Milliseconds(), "baseline_files_bytes": baselineTB.bytes(), "derived_files_bytes": derivedTB.bytes(), "query_count_plus_page_p50_ms": float64(latencies[49]) / float64(time.Millisecond), "query_count_plus_page_p95_ms": float64(latencies[94]) / float64(time.Millisecond), "query_count_plus_page_p99_ms": float64(latencies[98]) / float64(time.Millisecond), "samples": len(latencies), "index_optimization": "none", "scope": "ObjectStore list-query probe; no production projector lifecycle or iPad"}
			encoded, err := json.Marshal(row)
			if err != nil {
				t.Fatal(err)
			}
			fmt.Printf("PINKHA_NATIVE_BENCHMARK %s\n", encoded)
		})
	}
}
