package app
// Explicit immutable component lookup fixture; no any-sync initialization/run.
type App struct { Components map[string]any }
func (a *App) Component(name string) any { return a.Components[name] }
