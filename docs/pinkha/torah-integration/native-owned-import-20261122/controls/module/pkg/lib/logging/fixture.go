package logging
type Logger struct{}
func LoggerNotSugared(string) Logger{return Logger{}}
func (Logger) Error(string,...any){}
