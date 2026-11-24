// This bounded conversion utility emits private content. Redirect its output
// to a protected file; never attach it to public CI logs.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	projection "pinkha.local/semanticprojection"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "semantic projection refused:", err)
		os.Exit(1)
	}
}

func run() error {
	raw, err := io.ReadAll(io.LimitReader(os.Stdin, 400001))
	if err != nil {
		return err
	}
	if len(raw) > 400000 {
		return projection.ErrLimit
	}
	var input struct {
		Source  string `json:"source"`
		Literal bool   `json:"literal"`
	}
	if err := json.Unmarshal(raw, &input); err != nil {
		return err
	}
	p, err := projection.ProjectInline(input.Source, input.Literal)
	if err != nil {
		return err
	}
	return json.NewEncoder(os.Stdout).Encode(p)
}
