package localstorewitness

import (
	"bytes"
	"context"
	"errors"
	"math"

	"github.com/anyproto/any-store/anyenc"
)

// Encoding names a detached re-encoding of the decoded Value exposed by native
// Doc.Value. It is not the original SQLite BLOB, database page, or file bytes.
const Encoding = "anyenc-v1.0.3-decoded-value-roundtrip-v1"

var ErrUnsupportedValue = errors.New("unsupported or non-lossless decoded native value")

type valueBudget struct {
	bytes  int64
	nodes  int
	limits Limits
}

// measure validates before MarshalTo allocates its detached output. The native
// driver has already decoded the row; these limits do not bound driver decoding.
func (b *valueBudget) measure(ctx context.Context, v *anyenc.Value, depth int) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if v == nil || depth > b.limits.MaxDepth {
		return ErrUnsupportedValue
	}
	b.nodes++
	if b.nodes > b.limits.MaxValueNodes {
		return ErrLimit
	}
	b.bytes++
	switch v.Type() {
	case anyenc.TypeNull, anyenc.TypeTrue, anyenc.TypeFalse:
	case anyenc.TypeNumber:
		b.bytes += 8
	case anyenc.TypeString, anyenc.TypeBinary:
		var raw []byte
		var err error
		if v.Type() == anyenc.TypeString {
			raw, err = v.StringBytes()
			b.bytes++
		} else {
			raw, err = v.Bytes()
			b.bytes += 4
		}
		if err != nil {
			return ErrUnsupportedValue
		}
		b.bytes += int64(len(raw))
	case anyenc.TypeArray:
		values, err := v.Array()
		if err != nil {
			return ErrUnsupportedValue
		}
		b.bytes++
		for _, child := range values {
			if err := b.measure(ctx, child, depth+1); err != nil {
				return err
			}
		}
	case anyenc.TypeObject:
		obj, err := v.Object()
		if err != nil {
			return ErrUnsupportedValue
		}
		b.bytes++
		var visitErr error
		obj.Visit(func(key []byte, child *anyenc.Value) {
			if visitErr != nil {
				return
			}
			b.bytes += int64(len(key) + 1)
			if len(key) == 0 {
				b.bytes++
			}
			if b.bytes > b.limits.MaxRowBytes {
				visitErr = ErrLimit
				return
			}
			visitErr = b.measure(ctx, child, depth+1)
		})
		if visitErr != nil {
			return visitErr
		}
	default:
		return ErrUnsupportedValue
	}
	if b.bytes > b.limits.MaxRowBytes {
		return ErrLimit
	}
	return nil
}

type pair struct {
	key   []byte
	value *anyenc.Value
}

func pairs(v *anyenc.Value) []pair {
	obj, _ := v.Object()
	out := make([]pair, 0, obj.Len())
	obj.Visit(func(key []byte, child *anyenc.Value) { out = append(out, pair{key: key, value: child}) })
	return out
}

// equalDecoded compares exposed values, including ordered duplicate object
// entries, byte-valued strings/binary, and float64 bits (including signed zero).
func equalDecoded(a, b *anyenc.Value) bool {
	if a == nil || b == nil {
		return a == nil && b == nil
	}
	if a.Type() != b.Type() {
		return false
	}
	switch a.Type() {
	case anyenc.TypeNull, anyenc.TypeTrue, anyenc.TypeFalse:
		return true
	case anyenc.TypeNumber:
		x, _ := a.Float64()
		y, _ := b.Float64()
		return math.Float64bits(x) == math.Float64bits(y)
	case anyenc.TypeString:
		x, _ := a.StringBytes()
		y, _ := b.StringBytes()
		return bytes.Equal(x, y)
	case anyenc.TypeBinary:
		x, _ := a.Bytes()
		y, _ := b.Bytes()
		return bytes.Equal(x, y)
	case anyenc.TypeArray:
		x, _ := a.Array()
		y, _ := b.Array()
		if len(x) != len(y) {
			return false
		}
		for i := range x {
			if !equalDecoded(x[i], y[i]) {
				return false
			}
		}
		return true
	case anyenc.TypeObject:
		x, y := pairs(a), pairs(b)
		if len(x) != len(y) {
			return false
		}
		for i := range x {
			if !bytes.Equal(x[i].key, y[i].key) || !equalDecoded(x[i].value, y[i].value) {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func detachValue(ctx context.Context, v *anyenc.Value, limits Limits) ([]byte, error) {
	b := valueBudget{limits: limits}
	if err := b.measure(ctx, v, 0); err != nil {
		return nil, err
	}
	encoded := v.MarshalTo(nil)
	if int64(len(encoded)) > limits.MaxRowBytes {
		return nil, ErrLimit
	}
	decoded, err := anyenc.Parse(encoded)
	if err != nil || !equalDecoded(v, decoded) {
		return nil, ErrUnsupportedValue
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return encoded, nil
}

// uniqueField rejects ambiguous top-level identity/binding fields. Unrelated
// ordered fields remain preserved in the detached decoded-value representation.
func uniqueField(v *anyenc.Value, name string) (*anyenc.Value, error) {
	if v == nil || v.Type() != anyenc.TypeObject {
		return nil, ErrUnsupportedValue
	}
	var found *anyenc.Value
	n := 0
	obj, _ := v.Object()
	obj.Visit(func(key []byte, child *anyenc.Value) {
		if bytes.Equal(key, []byte(name)) {
			found = child
			n++
		}
	})
	if n != 1 || found == nil {
		return nil, ErrUnsupportedValue
	}
	return found, nil
}
