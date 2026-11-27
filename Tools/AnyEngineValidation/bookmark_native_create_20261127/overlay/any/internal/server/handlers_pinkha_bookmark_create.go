package server

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"unicode/utf8"

	"github.com/anyproto/any-sync-sdk/space"
	"github.com/labstack/echo/v4"
)

const maxBookmarkCreateRequestBytes = 2 * 1024 * 1024

// validateBookmarkJSON refuses duplicate keys before extraction. The ordinary
// API keeps its original parser; this applies only to the opt-in condition and
// its closed read request. Bounds include nested initial-property values.
func validateBookmarkJSON(raw []byte) error {
	if len(raw) == 0 || len(raw) > maxBookmarkCreateRequestBytes || !utf8.Valid(raw) {
		return space.ErrBookmarkCreateInvalid
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	nodes := 0
	var value func(int) error
	value = func(depth int) error {
		nodes++
		if depth > 32 || nodes > 65536 {
			return space.ErrBookmarkCreateInvalid
		}
		token, err := d.Token()
		if err != nil {
			return space.ErrBookmarkCreateInvalid
		}
		open, container := token.(json.Delim)
		if !container {
			return nil
		}
		switch open {
		case '{':
			seen := map[string]bool{}
			for d.More() {
				keyToken, err := d.Token()
				if err != nil {
					return space.ErrBookmarkCreateInvalid
				}
				key, ok := keyToken.(string)
				if !ok || seen[key] {
					return space.ErrBookmarkCreateInvalid
				}
				seen[key] = true
				if err := value(depth + 1); err != nil {
					return err
				}
			}
			close, err := d.Token()
			if err != nil || close != json.Delim('}') {
				return space.ErrBookmarkCreateInvalid
			}
		case '[':
			for d.More() {
				if err := value(depth + 1); err != nil {
					return err
				}
			}
			close, err := d.Token()
			if err != nil || close != json.Delim(']') {
				return space.ErrBookmarkCreateInvalid
			}
		default:
			return space.ErrBookmarkCreateInvalid
		}
		return nil
	}
	if err := value(0); err != nil {
		return err
	}
	if _, err := d.Token(); err != io.EOF {
		return space.ErrBookmarkCreateInvalid
	}
	return nil
}

func (d *deps) pinkhaBookmarkCreateFrame(c echo.Context) error {
	sp, response, done := d.resolveSpace(c)
	if done {
		return response
	}
	body, err := readBody(c)
	if err != nil || len(body) > 256*1024 || validateBookmarkJSON(body) != nil {
		return writeError(c, http.StatusBadRequest, "pinkha.bookmark_create_invalid", "invalid closed Bookmark frame request", nil)
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(body, &fields); err != nil || len(fields) != 2 || fields["typeId"] == nil || fields["collections"] == nil {
		return writeError(c, http.StatusBadRequest, "pinkha.bookmark_create_invalid", "exact typeId and collections fields required", nil)
	}
	var typeID string
	var collections []string
	if err := json.Unmarshal(fields["typeId"], &typeID); err != nil {
		return writeError(c, http.StatusBadRequest, "pinkha.bookmark_create_invalid", "typeId must be a string", nil)
	}
	if err := json.Unmarshal(fields["collections"], &collections); err != nil || collections == nil {
		return writeError(c, http.StatusBadRequest, "pinkha.bookmark_create_invalid", "collections must be an array of strings", nil)
	}
	proof, err := space.ReadBookmarkCreateFrame(c.Request().Context(), sp, typeID, collections)
	if err != nil {
		if response, handled := pinkhaBookmarkError(c, err); handled {
			return response
		}
		return pinkhaReadError(c, err, sp.Id())
	}
	return c.JSON(http.StatusOK, proof)
}

func pinkhaBookmarkError(c echo.Context, err error) (error, bool) {
	switch {
	case errors.Is(err, space.ErrBookmarkCreateInvalid):
		return writeError(c, http.StatusBadRequest, "pinkha.bookmark_create_invalid", "invalid closed Bookmark definition condition", nil), true
	case errors.Is(err, space.ErrBookmarkCreateChanged):
		return writeError(c, http.StatusConflict, "pinkha.bookmark_definition_changed", "selected Bookmark definitions changed; read a new frame before a new intent", nil), true
	case errors.Is(err, space.ErrBookmarkCreateIneligible):
		return writeError(c, http.StatusConflict, "pinkha.bookmark_definition_ineligible", "current definitions do not satisfy the imported Bookmark contract", nil), true
	case errors.Is(err, space.ErrCurrentWriterUnavailable):
		return writeError(c, http.StatusServiceUnavailable, "pinkha.current_writer_unavailable", "native Bookmark creation contract unavailable", nil), true
	}
	return nil, false
}
