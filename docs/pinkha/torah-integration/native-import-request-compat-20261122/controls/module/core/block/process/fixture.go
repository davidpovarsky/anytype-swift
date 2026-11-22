package process
type Progress interface { TryStep(int64) error }
