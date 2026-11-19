// Package pinkhat2test exists only in the separately pinned Go test composition.
// It is not copied into a product source inventory or a released runtime.
package pinkhat2test

import (
	"context"
	"errors"
	"reflect"
	"sync"
	"time"
)

type Filter struct {
	Stage     string
	ID        string
	Qualifier string
	Identity  any
	Pause     bool
}

type Event struct {
	Sequence  int    `json:"sequence"`
	Stage     string `json:"stage"`
	ID        string `json:"id"`
	Qualifier string `json:"qualifier"`
}

type watch struct {
	filter  Filter
	arrived chan Event
	resume  chan struct{}
	once    sync.Once
}

type Capture struct {
	mu         sync.Mutex
	watches    map[string]*watch
	events     []Event
	identities map[string]any
	counts     map[string]int
	timeouts   []string
	closed     bool
}

var active struct {
	sync.Mutex
	capture *Capture
}

func Begin(filters []Filter) (*Capture, error) {
	active.Lock()
	defer active.Unlock()
	if active.capture != nil || len(filters) == 0 {
		return nil, errors.New("one explicit lifecycle capture required")
	}
	c := &Capture{watches: map[string]*watch{}, identities: map[string]any{}, counts: map[string]int{}}
	for _, filter := range filters {
		if filter.Stage == "" || c.watches[filter.Stage] != nil {
			return nil, errors.New("unique named lifecycle stages required")
		}
		c.watches[filter.Stage] = &watch{filter: filter, arrived: make(chan Event, 1), resume: make(chan struct{})}
	}
	active.capture = c
	return c, nil
}

// Point never calls application code, changes a return value, replaces a context
// or token, retries work, or acquires a native lock. Only the explicit test gate
// may wait. Every wait is bounded, including failure cleanup and cancellation.
func Point(ctx context.Context, stage, id, qualifier string, identity any) {
	active.Lock()
	c := active.capture
	active.Unlock()
	if c == nil {
		return
	}
	c.mu.Lock()
	w := c.watches[stage]
	if c.closed || w == nil || w.filter.ID != id || w.filter.Qualifier != qualifier ||
		(w.filter.Identity != nil && w.filter.Identity != identity) {
		c.mu.Unlock()
		return
	}
	event := Event{Sequence: len(c.events) + 1, Stage: stage, ID: id, Qualifier: qualifier}
	c.events = append(c.events, event)
	c.counts[stage]++
	if c.counts[stage] == 1 {
		c.identities[stage] = identity
	}
	c.mu.Unlock()
	select {
	case w.arrived <- event:
	default:
	}
	if !w.filter.Pause {
		return
	}
	timer := time.NewTimer(20 * time.Second)
	defer timer.Stop()
	select {
	case <-w.resume:
	case <-ctx.Done():
	case <-timer.C:
		c.mu.Lock()
		c.timeouts = append(c.timeouts, stage)
		c.mu.Unlock()
	}
}

func TypeName[T any]() string { return reflect.TypeFor[T]().String() }

func (c *Capture) Arrival(stage string) <-chan Event { return c.watches[stage].arrived }

func (c *Capture) Release(stage string) {
	w := c.watches[stage]
	w.once.Do(func() { close(w.resume) })
}

func (c *Capture) Seen(stage string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.counts[stage] > 0
}

func (c *Capture) SameIdentity(first, second string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.identities[first] != nil && c.identities[first] == c.identities[second]
}

func (c *Capture) Report() map[string]any {
	c.mu.Lock()
	defer c.mu.Unlock()
	events := append([]Event{}, c.events...)
	counts := map[string]int{}
	for key, count := range c.counts {
		counts[key] = count
	}
	return map[string]any{"events": events, "counts": counts, "gate_timeouts": append([]string{}, c.timeouts...)}
}

func (c *Capture) Close() {
	c.mu.Lock()
	c.closed = true
	c.mu.Unlock()
	for stage := range c.watches {
		c.Release(stage)
	}
	active.Lock()
	if active.capture == c {
		active.capture = nil
	}
	active.Unlock()
}
