// Package pinkhat2spaceclosetest is present only in this separate test compile
// overlay. Its observations never grant authority or perform native work.
package pinkhat2spaceclosetest

import (
	"context"
	"errors"
	"sync"
	"time"
)

const maxEvents = 64

type Filter struct {
	Stage    string
	ID       string
	Identity any
	Pause    bool
}

type Event struct {
	Sequence int    `json:"sequence"`
	Stage    string `json:"stage"`
	ID       string `json:"id"`
	Result   string `json:"result"`
}

type watch struct {
	filter  Filter
	arrived chan Event
	resume  chan struct{}
	once    sync.Once
}

type Capture struct {
	mu            sync.Mutex
	watches       map[string]*watch
	events        []Event
	identities    map[string]any
	counts        map[string]int
	timeouts      []string
	cancellations []string
	overflow      bool
	closed        bool
}

var active struct {
	sync.Mutex
	capture *Capture
}

func Begin(filters []Filter) (*Capture, error) {
	active.Lock()
	defer active.Unlock()
	if active.capture != nil || len(filters) == 0 || len(filters) > 32 {
		return nil, errors.New("one bounded explicit Space close capture required")
	}
	c := &Capture{watches: map[string]*watch{}, identities: map[string]any{}, counts: map[string]int{}}
	for _, filter := range filters {
		if filter.Stage == "" || filter.ID == "" || c.watches[filter.Stage] != nil {
			return nil, errors.New("unique named stages and exact native IDs required")
		}
		c.watches[filter.Stage] = &watch{filter: filter, arrived: make(chan Event, 1), resume: make(chan struct{})}
	}
	active.capture = c
	return c, nil
}

// Point only records the selected native identity and optionally waits at the
// owner-selected barrier. It calls no application callback, changes no native
// result/context/token, and never acquires or releases a native lock. Both the
// event list and waits are bounded; unknown events are ignored, never invented.
func Point(ctx context.Context, stage, id, result string, identity any) {
	active.Lock()
	c := active.capture
	active.Unlock()
	if c == nil {
		return
	}
	c.mu.Lock()
	w := c.watches[stage]
	if c.closed || w == nil || w.filter.ID != id || (w.filter.Identity != nil && w.filter.Identity != identity) {
		c.mu.Unlock()
		return
	}
	if len(c.events) >= maxEvents {
		c.overflow = true
		c.mu.Unlock()
		return
	}
	event := Event{Sequence: len(c.events) + 1, Stage: stage, ID: id, Result: result}
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
	timer := time.NewTimer(40 * time.Second)
	defer timer.Stop()
	select {
	case <-w.resume:
	case <-ctx.Done():
		c.mu.Lock()
		c.cancellations = append(c.cancellations, stage)
		c.mu.Unlock()
	case <-timer.C:
		c.mu.Lock()
		c.timeouts = append(c.timeouts, stage)
		c.mu.Unlock()
	}
}

func Return(ctx context.Context, stage, id string, identity any, err error) {
	result := "OK"
	if err != nil {
		result = "ERROR"
	}
	Point(ctx, stage, id, result, identity)
}

func (c *Capture) Arrival(stage string) <-chan Event { return c.watches[stage].arrived }
func (c *Capture) Release(stage string)              { w := c.watches[stage]; w.once.Do(func() { close(w.resume) }) }
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
	counts := map[string]int{}
	for key, count := range c.counts {
		counts[key] = count
	}
	return map[string]any{"events": append([]Event{}, c.events...), "counts": counts,
		"gate_timeouts": append([]string{}, c.timeouts...), "gate_cancellations": append([]string{}, c.cancellations...),
		"overflow": c.overflow}
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
