//go:build pinkha_loaded_account_witness

package localstorewitness

import "sort"

// NativeRetainedCollection names a captured collection without inventing a
// semantic interpretation. Its original rows remain in the private witness.
type NativeRetainedCollection struct {
	Name  string
	Rows  int
	Bytes int64
}

func (n *NativeTreeInventory) SettingsTreeID() string {
	if n == nil || !n.complete {
		return ""
	}
	return n.settingsID
}

func (n *NativeTreeInventory) RetainedOtherCollections() []NativeRetainedCollection {
	if n == nil || !n.complete || n.witness == nil {
		return nil
	}
	var result []NativeRetainedCollection
	for _, col := range n.witness.collections {
		if col.name != "state" && col.name != "heads" && col.name != "changes" && col.name != n.acl.ACLID() {
			result = append(result, NativeRetainedCollection{Name: col.name, Rows: len(col.rows), Bytes: col.bytes})
		}
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Name < result[j].Name })
	return result
}
