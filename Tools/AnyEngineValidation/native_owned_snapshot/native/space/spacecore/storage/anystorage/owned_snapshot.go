package anystorage

import (
	"context"
	"crypto/rand"
	"errors"
	"math"
	"sync"

	anystore "github.com/anyproto/any-store"
	"github.com/anyproto/any-sync/commonspace/spacestorage"
)

// ErrSnapshotOwnership means that the exact native service/handle generation
// can no longer supply a read lease. It says nothing about account or ACL rights.
var ErrSnapshotOwnership = errors.New("current native owned storage handle required")

// LocalSnapshotBinding identifies one native service and one registered handle.
// The nonce is private evidence; public consumers should publish only its hash.
type LocalSnapshotBinding struct {
	OwnerNonce [32]byte
	Generation uint64
	SpaceID    string
}

// LocalSnapshotCapability has no public owner, storage, callback, or authority
// constructor. Only successful native service construction registers its handle.
// Its reviewed production consumer is the bounded localstorewitness reader;
// Go does not enforce exclusive use by that package.
type LocalSnapshotCapability struct {
	handle *snapshotHandle
}

// LocalSnapshotSource is an optional native storage feature. Generic wrappers
// made with NewClientStorage remain unowned and cannot issue a capability.
type LocalSnapshotSource interface {
	LocalSnapshotCapability() (*LocalSnapshotCapability, error)
}

// LocalSnapshotLease holds the existing per-space gate and the exact handle.
// The caller must finish its read transaction before Close. This slice has one
// reviewed production consumer that enforces that ordering. No mutation helper
// or arbitrary owner callback is supplied.
type LocalSnapshotLease struct {
	self    *LocalSnapshotLease
	handle  *snapshotHandle
	binding LocalSnapshotBinding
	ctx     context.Context
	cancel  context.CancelFunc
	unlock  func()

	// Protected by handle.owner.mu.
	released   bool
	releaseErr error
}

type snapshotOwner struct {
	mu         sync.Mutex
	closed     bool
	nonce      [32]byte
	generation uint64
	handles    map[*clientStorage]*snapshotHandle
}

type snapshotHandle struct {
	owner   *snapshotOwner
	service *storageService
	client  *clientStorage
	storage spacestorage.SpaceStorage
	db      anystore.DB
	binding LocalSnapshotBinding

	// Protected by owner.mu. No wait or native close holds that mutex.
	revoked      bool
	closing      bool
	closed       bool
	closeStarted bool
	closeErr     error
	closeDone    chan struct{}
	drained      chan struct{}
	leases       map[*LocalSnapshotLease]struct{}
}

func (o *snapshotOwner) accepting() error {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.closed {
		return ErrSnapshotOwnership
	}
	return nil
}

// Called only by Wait/Create while their existing per-space gate is held.
// The recheck after native initialization prevents registration after shutdown.
func (s *storageService) newOwnedClientStorage(ctx context.Context, storage spacestorage.SpaceStorage) (*clientStorage, error) {
	client, err := NewClientStorage(ctx, storage)
	if err != nil {
		return nil, err
	}
	o := &s.snapshots
	o.mu.Lock()
	if ctx.Err() != nil || o.closed || storage == nil || storage.Id() == "" || storage.AnyStore() == nil || o.generation == math.MaxUint64 {
		o.mu.Unlock()
		return nil, errors.Join(ErrSnapshotOwnership, ctx.Err(), client.closeStorage(ctx))
	}
	if o.nonce == ([32]byte{}) {
		var nonce [32]byte
		if _, err = rand.Read(nonce[:]); err != nil || nonce == ([32]byte{}) {
			o.mu.Unlock()
			return nil, errors.Join(ErrSnapshotOwnership, err, client.closeStorage(ctx))
		}
		o.nonce = nonce
	}
	if o.handles == nil {
		o.handles = make(map[*clientStorage]*snapshotHandle)
	}
	o.generation++
	drained := make(chan struct{})
	close(drained)
	h := &snapshotHandle{
		owner: o, service: s, client: client, storage: storage, db: storage.AnyStore(),
		binding:   LocalSnapshotBinding{OwnerNonce: o.nonce, Generation: o.generation, SpaceID: storage.Id()},
		closeDone: make(chan struct{}), drained: drained, leases: make(map[*LocalSnapshotLease]struct{}),
	}
	client.snapshot = h
	o.handles[client] = h
	o.mu.Unlock()
	return client, nil
}

func (o *snapshotOwner) currentLocked(h *snapshotHandle) error {
	if h == nil || h.owner != o || o.closed || h.revoked || h.closing || h.closed ||
		o.handles[h.client] != h || h.client.snapshot != h ||
		h.client.SpaceStorage != h.storage || h.storage.AnyStore() != h.db ||
		h.binding.OwnerNonce != o.nonce || h.binding.Generation == 0 ||
		h.binding.SpaceID == "" || h.storage.Id() != h.binding.SpaceID {
		return ErrSnapshotOwnership
	}
	return nil
}

func (r *clientStorage) LocalSnapshotCapability() (*LocalSnapshotCapability, error) {
	if r == nil || r.snapshot == nil {
		return nil, ErrSnapshotOwnership
	}
	h := r.snapshot
	h.owner.mu.Lock()
	defer h.owner.mu.Unlock()
	if err := h.owner.currentLocked(h); err != nil {
		return nil, err
	}
	return &LocalSnapshotCapability{handle: h}, nil
}

func (c *LocalSnapshotCapability) AcquireWitnessLease(ctx context.Context) (*LocalSnapshotLease, error) {
	if ctx == nil || c == nil || c.handle == nil {
		return nil, ErrSnapshotOwnership
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	h := c.handle
	o := h.owner
	o.mu.Lock()
	err := o.currentLocked(h)
	o.mu.Unlock()
	if err != nil {
		return nil, err
	}
	unlock, err := h.service.lockSpace(ctx, h.binding.SpaceID)
	if err != nil {
		return nil, err
	}
	// lockSpace's select can choose a ready gate even when ctx was canceled.
	// Check again before counting a lease or exposing its native handle.
	o.mu.Lock()
	if err = errors.Join(ctx.Err(), o.currentLocked(h)); err != nil {
		o.mu.Unlock()
		unlock()
		return nil, err
	}
	leaseCtx, cancel := context.WithCancel(ctx)
	if err = leaseCtx.Err(); err != nil {
		o.mu.Unlock()
		cancel()
		unlock()
		return nil, err
	}
	l := &LocalSnapshotLease{handle: h, binding: h.binding, ctx: leaseCtx, cancel: cancel, unlock: unlock}
	l.self = l
	if len(h.leases) == 0 {
		h.drained = make(chan struct{})
	}
	h.leases[l] = struct{}{}
	o.mu.Unlock()
	return l, nil
}

func (l *LocalSnapshotLease) Context() context.Context {
	if l == nil || l.self != l {
		return nil
	}
	return l.ctx
}

func (l *LocalSnapshotLease) Binding() LocalSnapshotBinding {
	if l == nil || l.self != l {
		return LocalSnapshotBinding{}
	}
	return l.binding
}

func (l *LocalSnapshotLease) Storage() spacestorage.SpaceStorage {
	if l == nil || l.self != l || l.handle == nil {
		return nil
	}
	return l.handle.client
}

func (l *LocalSnapshotLease) CheckCurrent(ctx context.Context) error {
	if ctx == nil || l == nil || l.self != l || l.handle == nil {
		return ErrSnapshotOwnership
	}
	o := l.handle.owner
	o.mu.Lock()
	defer o.mu.Unlock()
	if l.released || l.binding != l.handle.binding {
		return ErrSnapshotOwnership
	}
	if _, ok := l.handle.leases[l]; !ok {
		return ErrSnapshotOwnership
	}
	return errors.Join(ctx.Err(), l.ctx.Err(), o.currentLocked(l.handle))
}

// Close never exits before releasing its count and gate, including revocation.
// The final current check and release are one owner-mutex linearization point.
func (l *LocalSnapshotLease) Close() error {
	if l == nil || l.self != l || l.handle == nil {
		return ErrSnapshotOwnership
	}
	h := l.handle
	o := h.owner
	o.mu.Lock()
	if l.released {
		err := l.releaseErr
		o.mu.Unlock()
		return err
	}
	// Private fields do not prevent a Go value copy. Only the original
	// registered lease may cancel, decrement, or unlock the shared gate.
	if _, present := h.leases[l]; !present {
		o.mu.Unlock()
		return ErrSnapshotOwnership
	}
	l.releaseErr = errors.Join(l.ctx.Err(), o.currentLocked(h))
	l.released = true
	delete(h.leases, l)
	if len(h.leases) == 0 {
		close(h.drained)
	}
	err := l.releaseErr
	o.mu.Unlock()
	l.cancel()
	l.unlock()
	return err
}

func (h *snapshotHandle) revokeLocked() {
	h.revoked = true
	for l := range h.leases {
		l.cancel()
	}
}

// Existing native handle destruction happens only after all its leases drain.
// The context bounds waiting; vendor transaction commit/database cleanup retain
// their existing behavior and are not claimed to obey an end-to-end deadline.
func (h *snapshotHandle) close(ctx context.Context) error {
	if ctx == nil {
		return ErrSnapshotOwnership
	}
	o := h.owner
	for {
		o.mu.Lock()
		if h.closed {
			err := h.closeErr
			o.mu.Unlock()
			return err
		}
		h.closing = true
		h.revokeLocked()
		if err := ctx.Err(); err != nil {
			o.mu.Unlock()
			return err
		}
		if len(h.leases) == 0 && !h.closeStarted {
			h.closeStarted = true
			o.mu.Unlock()
			err := h.client.closeStorage(ctx)
			o.mu.Lock()
			h.closeErr = err
			h.closed = true
			delete(o.handles, h.client)
			close(h.closeDone)
			o.mu.Unlock()
			return err
		}
		wait := h.drained
		if h.closeStarted {
			wait = h.closeDone
		}
		o.mu.Unlock()
		select {
		case <-wait:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

// The caller already holds the existing per-space gate, so every owned snapshot
// for this exact Space has drained. Other DB handles for the Space all lose
// eligibility, including handles detached by a successful recovery rename.
func (o *snapshotOwner) revokeSpace(spaceID string) {
	o.mu.Lock()
	defer o.mu.Unlock()
	for _, h := range o.handles {
		if h.binding.SpaceID == spaceID {
			h.revokeLocked()
		}
	}
}

func (o *snapshotOwner) close(ctx context.Context) error {
	if ctx == nil {
		return ErrSnapshotOwnership
	}
	o.mu.Lock()
	o.closed = true
	wait := make([]<-chan struct{}, 0, len(o.handles))
	for _, h := range o.handles {
		h.revokeLocked()
		wait = append(wait, h.drained)
	}
	o.mu.Unlock()
	for _, drained := range wait {
		select {
		case <-drained:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	return ctx.Err()
}
