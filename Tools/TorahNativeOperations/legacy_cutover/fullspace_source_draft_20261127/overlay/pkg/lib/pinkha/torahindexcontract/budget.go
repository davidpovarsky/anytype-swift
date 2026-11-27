package torahindexcontract

import "github.com/anyproto/any-store/anyenc"

// Budget is shared by H1, the index snapshot and H2. Count each independently
// enumerated collection against MaxObjects, and all retained bytes together.
type Budget struct{ used int }

func (b *Budget) Add(length int) error {
	if b == nil || length < 0 || length > MaxWitnessBytes-b.used {
		return ErrBound
	}
	b.used += length
	return nil
}

func (b *Budget) Used() int {
	if b == nil {
		return 0
	}
	return b.used
}

// Value bounds the borrowed native value before JSON conversion/copying. It
// does not allocate a serialized copy merely to find an oversized row.
func (b *Budget) Value(value *anyenc.Value) error { return b.value(value, 0) }

func (b *Budget) value(value *anyenc.Value, depth int) error {
	if value == nil {
		return ErrInvalidWitness
	}
	if depth > 64 {
		return ErrBound
	}
	if err := b.Add(9); err != nil {
		return err
	}
	switch value.Type() {
	case anyenc.TypeNull, anyenc.TypeNumber, anyenc.TypeFalse, anyenc.TypeTrue:
		return nil
	case anyenc.TypeString:
		return b.Add(len(value.GetStringBytes()))
	case anyenc.TypeBinary:
		return b.Add(len(value.GetBytes()))
	case anyenc.TypeArray:
		values := value.GetArray()
		if len(values) > (MaxWitnessBytes-b.used)/9 {
			return ErrBound
		}
		for _, item := range values {
			if err := b.value(item, depth+1); err != nil {
				return err
			}
		}
	case anyenc.TypeObject:
		object := value.GetObject()
		if object.Len() > (MaxWitnessBytes-b.used)/9 {
			return ErrBound
		}
		var err error
		object.Visit(func(key []byte, item *anyenc.Value) {
			if err != nil {
				return
			}
			if err = b.Add(len(key)); err == nil {
				err = b.value(item, depth+1)
			}
		})
		return err
	default:
		return ErrInvalidWitness
	}
	return nil
}
