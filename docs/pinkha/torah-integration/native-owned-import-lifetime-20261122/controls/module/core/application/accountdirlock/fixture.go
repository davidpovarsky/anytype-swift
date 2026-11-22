package accountdirlock
// In-memory lease ABI fixture. No filesystem lock, acquisition or erasure.
type Lease struct { Root, AccountID string; IsUsable bool; Releases int; ReleaseError error }
func (l *Lease) Matches(root, account string) bool { return l.Root == root && l.AccountID == account }
func (l *Lease) Usable() bool { return l.IsUsable }
func (l *Lease) Release() error { l.Releases++; return l.ReleaseError }
