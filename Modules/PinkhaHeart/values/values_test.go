package torahvalues

import (
	"encoding/json"
	"github.com/anyproto/anytype-heart/core/domain"
	torah "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"
	"testing"
)

func TestCanonicalExportAndHumanSearch(t *testing.T) {
	canonical := "  {\"version\":2,\"records\":[],\"unknownFields\":{\"keep\":true}}\n"
	labels, _ := json.Marshal(map[string]torah.DisplayLabel{"identity": {Hebrew: "בריאה", English: "Creation"}})
	d := domain.NewDetails().SetString("actual-canonical-key", canonical).SetString("ordinary-property", "unchanged")
	for _, key := range torah.LocalKeys() {
		d.SetString(domain.RelationKey(key), "internal")
	}
	d.SetBool(domain.RelationKey(torah.ReadyKey), true).SetString(domain.RelationKey(torah.LabelsKey), string(labels)).SetStringList(domain.RelationKey(torah.TopicsKey), []string{"identity"})
	exported := ExportDetails(d)
	if exported.GetString("actual-canonical-key") != canonical || exported.GetString("ordinary-property") != "unchanged" {
		t.Fatal("export changed canonical or ordinary Anytype data")
	}
	for _, key := range torah.LocalKeys() {
		if exported.Has(domain.RelationKey(key)) {
			t.Fatal("export leaked local cache: " + key)
		}
	}
	if !d.Has(domain.RelationKey(torah.LabelsKey)) {
		t.Fatal("export mutated live state")
	}
	if text := SearchText(d, torah.TopicsKey); text != "בריאה\nCreation" {
		t.Fatalf("not human text: %q", text)
	}
	d.SetBool(domain.RelationKey(torah.ReadyKey), false)
	if SearchText(d, torah.TopicsKey) != "" {
		t.Fatal("invalid/unready projection was indexed as text")
	}
}
