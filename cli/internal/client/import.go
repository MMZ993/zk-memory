package client

import "encoding/json"

type ImportOptions struct {
	Mode       string
	EntityType string
	EntityID   string
}

type importSelection struct {
	Type string `json:"type"`
	ID   string `json:"id"`
}

type importRequest struct {
	Document  json.RawMessage  `json:"document"`
	Mode      string           `json:"mode"`
	Selection *importSelection `json:"selection,omitempty"`
}

// ImportDocument analyzes or applies a canonical JSON import document.
func (c *Client) ImportDocument(document json.RawMessage, opts ImportOptions) (json.RawMessage, error) {
	mode := opts.Mode
	if mode == "" {
		mode = "dry_run"
	}
	request := importRequest{Document: document, Mode: mode}
	if opts.EntityType != "" || opts.EntityID != "" {
		request.Selection = &importSelection{Type: opts.EntityType, ID: opts.EntityID}
	}
	var out json.RawMessage
	if err := c.post("/api/import/", request, &out); err != nil {
		return nil, err
	}
	return out, nil
}
