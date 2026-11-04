package torahderived

const Version = 1
const SourcesKey = "pinkhaTorahSources"
const TopicsKey = "pinkhaTorahTopics"
const WordsKey = "pinkhaTorahWords"
const ReadyKey = "_pinkhaTorahReady"
const LabelsKey = "_pinkhaTorahLabels"
const VersionKey = "_pinkhaTorahProjectionVersion"
const CanonicalHashKey = "_pinkhaTorahCanonicalHash"
const StatusKey = "_pinkhaTorahState"
const CanonicalKeyKey = "_pinkhaTorahCanonicalPropertyKey"
const ManifestUniqueKey = "pinkha.space.manifest"

type PropertyDefinition struct {
	Kind Kind
	Key  string
	Name string
}

var Definitions = []PropertyDefinition{
	{Ref, SourcesKey, "מקור/ות"},
	{Topic, TopicsKey, "נושא"},
	{Word, WordsKey, "מילה / ערך"},
}

func IsProperty(key string) bool {
	return key == SourcesKey || key == TopicsKey || key == WordsKey
}

func LocalKeys() []string {
	return []string{SourcesKey, TopicsKey, WordsKey, ReadyKey, LabelsKey, VersionKey, CanonicalHashKey, StatusKey, CanonicalKeyKey}
}

func IsLocalKey(key string) bool {
	for _, candidate := range LocalKeys() {
		if key == candidate {
			return true
		}
	}
	return false
}
