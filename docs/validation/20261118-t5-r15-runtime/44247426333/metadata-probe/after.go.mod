module gobind

go 1.26.5

require (
	example.test/a v1.0.0
	example.test/b v1.1.0
)

replace (
	example.test/a v1.0.0 => ../a
	example.test/b v1.0.0 => ../b1
	example.test/b v1.1.0 => ../b2
)
