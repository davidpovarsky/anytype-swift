//go:build pinkha_torah_index_acceptance && pinkha_cutover_acceptance

package core

import "errors"

// PinkhaIndexAcceptanceStopAccount exposes only the original typed shutdown
// outcome to the generated-byte acceptance fixture. That fixture deliberately
// closes its own index DB, and must distinguish the exact expected DB-closed
// cleanup leaf from any unrelated teardown failure. Release builds do not
// contain this helper. It does not alter shutdown, authority or wire behavior.
func PinkhaIndexAcceptanceStopAccount(mw *Middleware) error {
	if mw == nil || mw.applicationService == nil {
		return errors.New("missing acceptance account owner")
	}
	return mw.applicationService.Stop()
}
