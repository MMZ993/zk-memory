package client

import "encoding/json"

// ExportAll calls GET /api/export and returns the raw JSON response.
func (c *Client) ExportAll() (json.RawMessage, error) {
	var out json.RawMessage
	if err := c.get("/api/export", &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ExportNotes calls GET /api/export/notes and returns the raw JSON response.
func (c *Client) ExportNotes() (json.RawMessage, error) {
	var out json.RawMessage
	if err := c.get("/api/export/notes", &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ExportBuffer calls GET /api/export/buffer and returns the raw JSON response.
func (c *Client) ExportBuffer() (json.RawMessage, error) {
	var out json.RawMessage
	if err := c.get("/api/export/buffer", &out); err != nil {
		return nil, err
	}
	return out, nil
}
