package format

import (
	"fmt"
	"strconv"
	"strings"
)

func validateID(id string) error {
	if id == "" || id == "." || id == ".." || strings.ContainsAny(id, `/\\`) {
		return fmt.Errorf("invalid export ID %q", id)
	}
	return nil
}

func yamlNullable(s *string) string {
	if s == nil {
		return "null"
	}
	return yamlQuoteTitle(*s)
}

func yamlQuoteTitle(s string) string {
	return strconv.Quote(s)
}
