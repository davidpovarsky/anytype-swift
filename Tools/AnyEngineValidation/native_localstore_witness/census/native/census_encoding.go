package localstorewitness

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"io"
)

type censusBoundedWriter struct {
	dst     io.Writer
	limit   int64
	written int64
}

func (w *censusBoundedWriter) Write(raw []byte) (int, error) {
	if int64(len(raw)) > w.limit-w.written {
		return 0, ErrLimit
	}
	n, err := w.dst.Write(raw)
	w.written += int64(n)
	if err == nil && n != len(raw) {
		err = io.ErrShortWrite
	}
	return n, err
}

type censusEncoder struct {
	dst io.Writer
	err error
}

func (e *censusEncoder) raw(value []byte) {
	if e.err != nil {
		return
	}
	n, err := e.dst.Write(value)
	e.err = err
	if e.err == nil && n != len(value) {
		e.err = io.ErrShortWrite
	}
}

func (e *censusEncoder) field(value []byte) {
	var size [8]byte
	binary.BigEndian.PutUint64(size[:], uint64(len(value)))
	e.raw(size[:])
	e.raw(value)
}

func (e *censusEncoder) text(value string) { e.field([]byte(value)) }

func (e *censusEncoder) integer(value int) {
	var number [8]byte
	binary.BigEndian.PutUint64(number[:], uint64(int64(value)))
	e.field(number[:])
}

// writePrivate is a deterministic length-framed representation. The nested
// witness is copied exactly; row/classification references are supplemental.
// Signed metadata integers use big-endian two's-complement int64; -1 is absent.
func (c *LocalTreeCensus) writePrivate(dst io.Writer) error {
	e := &censusEncoder{dst: dst}
	e.text("pinkha-local-tree-storage-census-v1")
	e.text("local-structural-identities-no-source-admission")
	e.text(c.witness.digest)
	sourceSize := &censusBoundedWriter{dst: io.Discard, limit: c.limits.MaxPrivateBytes}
	if err := c.witness.writePrivate(sourceSize); err != nil {
		return err
	}
	var size [8]byte
	binary.BigEndian.PutUint64(size[:], uint64(sourceSize.written))
	e.raw(size[:])
	if e.err != nil {
		return e.err
	}
	if err := c.witness.writePrivate(dst); err != nil {
		return err
	}
	e.integer(len(c.rows))
	for _, row := range c.rows {
		e.integer(row.collection)
		e.integer(row.ordinal)
		e.text(row.kind)
		e.field(row.nativeID)
		e.field(row.id)
		e.field(row.tree)
		e.integer(row.deleted)
		e.integer(row.derived)
		unresolved := 0
		if row.unresolved {
			unresolved = 1
		}
		e.integer(unresolved)
	}
	e.integer(len(c.references))
	for _, ref := range c.references {
		e.integer(ref.row)
		e.integer(ref.position)
		e.text(ref.kind)
		e.text(ref.domain)
		e.field(ref.field)
		e.field(ref.id)
		e.field(ref.tree)
		e.text(ref.outcome)
		e.integer(ref.target)
		e.integer(ref.observed)
	}
	e.integer(len(c.issues))
	for _, issue := range c.issues {
		e.integer(issue.collection)
		e.integer(issue.row)
		e.field(issue.field)
		e.integer(issue.position)
		e.text(issue.code)
	}
	return e.err
}

// WritePrivate exposes native identities and captured row values. Callers must
// use their explicit private fixture directory, never logs or public artifacts.
func (c *LocalTreeCensus) WritePrivate(dst io.Writer) error {
	if c == nil || !c.complete || c.witness == nil || !c.witness.complete || dst == nil {
		return ErrIncompleteCensus
	}
	h := sha256.New()
	bounded := &censusBoundedWriter{dst: io.MultiWriter(dst, h), limit: c.limits.MaxPrivateBytes}
	if err := c.writePrivate(bounded); err != nil {
		return err
	}
	if bounded.written != c.bytes || hex.EncodeToString(h.Sum(nil)) != c.digest {
		return ErrIncompleteCensus
	}
	return nil
}
