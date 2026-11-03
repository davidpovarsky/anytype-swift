// Package torahderived retains the original fixture API while exercising the
// production implementation used by Pinkha's native middleware integration.
package torahderived

import native "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah"

type Kind = native.Kind
type Binding = native.Binding
type Input = native.Input
type Projection = native.Projection
type ManifestSource = native.ManifestSource
type ManifestCandidate = native.ManifestCandidate
type PropertyDescriptor = native.PropertyDescriptor
type State = native.State
type Readiness = native.Readiness

const (
 Ref = native.Ref
 Topic = native.Topic
 Word = native.Word
 NotInitialized = native.NotInitialized
 Discovering = native.Discovering
 Rebuilding = native.Rebuilding
 Ready = native.Ready
 Outdated = native.Outdated
 Error = native.Error
 Unsupported = native.Unsupported
)

var (
 ErrMalformed = native.ErrMalformed
 ErrUnsupported = native.ErrUnsupported
 ErrBinding = native.ErrBinding
 ErrIneligible = native.ErrIneligible
 ErrNotReady = native.ErrNotReady
 ErrStaleGeneration = native.ErrStaleGeneration
 Identity = native.Identity
 Project = native.Project
 ResolveBinding = native.ResolveBinding
)
