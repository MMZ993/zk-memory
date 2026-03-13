package client

import (
	"encoding/json"
	"fmt"
	"net/url"
	"strconv"
)

// BufferNote represents a buffer note from the API.
type BufferNote struct {
	ID          string          `json:"id"`
	Content     string          `json:"content"`
	Meta        json.RawMessage `json:"meta,omitempty"`
	Processed   bool            `json:"processed"`
	ProcessedAt *string         `json:"processed_at,omitempty"`
	CreatedAt   string          `json:"created_at"`
	UpdatedAt   string          `json:"updated_at"`
}

// CreateBufferRequest is the request body for POST /api/buffer.
type CreateBufferRequest struct {
	Content string          `json:"content"`
	Meta    json.RawMessage `json:"meta,omitempty"`
}

// BufferListOpts holds optional parameters for ListBuffer.
type BufferListOpts struct {
	Processed *bool // nil = no filter
	Limit     int
	Offset    int
}

// AddBuffer calls POST /api/buffer.
func (c *Client) AddBuffer(req CreateBufferRequest) (*BufferNote, error) {
	var out BufferNote
	if err := c.post("/api/buffer", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ListBuffer calls GET /api/buffer.
func (c *Client) ListBuffer(opts BufferListOpts) ([]BufferNote, error) {
	params := url.Values{}
	if opts.Processed != nil {
		params.Set("processed", strconv.FormatBool(*opts.Processed))
	}
	if opts.Limit > 0 {
		params.Set("limit", strconv.Itoa(opts.Limit))
	}
	if opts.Offset > 0 {
		params.Set("offset", strconv.Itoa(opts.Offset))
	}
	var out []BufferNote
	if err := c.get("/api/buffer?"+params.Encode(), &out); err != nil {
		return nil, err
	}
	return out, nil
}

// GetBuffer calls GET /api/buffer/{id}.
func (c *Client) GetBuffer(id string) (*BufferNote, error) {
	var out BufferNote
	if err := c.get(fmt.Sprintf("/api/buffer/%s", id), &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// DeleteBuffer calls DELETE /api/buffer/{id}.
func (c *Client) DeleteBuffer(id string) error {
	return c.del(fmt.Sprintf("/api/buffer/%s", id), nil)
}

// ProcessBuffer calls POST /api/buffer/{id}/process.
func (c *Client) ProcessBuffer(id string) (*BufferNote, error) {
	var out BufferNote
	if err := c.post(fmt.Sprintf("/api/buffer/%s/process", id), nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CleanupBuffer calls DELETE /api/buffer/cleanup.
func (c *Client) CleanupBuffer() (map[string]any, error) {
	var out map[string]any
	if err := c.del("/api/buffer/cleanup", &out); err != nil {
		return nil, err
	}
	return out, nil
}
