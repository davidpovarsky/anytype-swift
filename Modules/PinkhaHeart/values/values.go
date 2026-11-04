// Package torahvalues adapts local projections to native export and full text.
package torahvalues

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"strings"

	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
)

// ExportDetails retains canonical bytes and every ordinary Anytype detail.
// Local index/cache fields are never transported to an older importer.
func ExportDetails(details *domain.Details) *domain.Details {
	result := details.Copy()
	for _, key := range torah.LocalKeys() {
		result.Delete(domain.RelationKey(key))
	}
	return result
}

func SearchText(details *domain.Details, key string) string {
	if details == nil {
		return ""
	}
	if !details.GetBool(domain.RelationKey(torah.ReadyKey)) || !torah.IsProperty(key) {
		return ""
	}
	var labels map[string]torah.DisplayLabel
	if json.Unmarshal([]byte(details.GetString(domain.RelationKey(torah.LabelsKey))), &labels) != nil {
		return ""
	}
	var text []string
	seen := map[string]bool{}
	for _, id := range details.GetStringList(domain.RelationKey(key)) {
		label := labels[id]
		for _, value := range []string{label.Hebrew, label.English} {
			value = strings.TrimSpace(value)
			if value != "" && !seen[value] {
				seen[value] = true
				text = append(text, value)
			}
		}
	}
	return strings.Join(text, "\n")
}

func SearchFingerprint(details *domain.Details) string {
	text := ""
	for _, definition := range torah.Definitions {
		text += definition.Key + "\x00" + SearchText(details, definition.Key) + "\x00"
	}
	if details != nil {
		text += details.GetString(domain.RelationKey(torah.CanonicalKeyKey))
	}
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}
