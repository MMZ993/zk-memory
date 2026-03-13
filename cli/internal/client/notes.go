package client

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"
)

// Note represents a note from the API.
type Note struct {
	ID        string   `json:"id"`
	Title     string   `json:"title"`
	Content   string   `json:"content"`
	Summary   string   `json:"summary,omitempty"`
	Tags      []string `json:"tags"`
	Links     []Link   `json:"links"`
	Synced    bool     `json:"synced"`
	CreatedAt string   `json:"created_at"`
	UpdatedAt string   `json:"updated_at"`
}

// Link represents a link between notes.
type Link struct {
	ID     string `json:"id"`
	NoteID string `json:"note_id"`
	LinkID string `json:"link_id"`
}

// SearchResult is one item in a search response.
type SearchResult struct {
	Note
	Score    float64 `json:"score"`
	Distance int     `json:"distance,omitempty"`
}

// SearchResponse is the full response from GET /api/notes/search.
type SearchResponse struct {
	Results []SearchResult `json:"results"`
	Total   int            `json:"total"`
}

// NoteListResponse is the full response from GET /api/notes.
type NoteListResponse = []Note

// CreateNoteRequest is the request body for POST /api/notes.
type CreateNoteRequest struct {
	Title   string   `json:"title"`
	Content string   `json:"content"`
	Summary string   `json:"summary,omitempty"`
	Tags    []string `json:"tags,omitempty"`
}

// UpdateNoteRequest is the request body for PATCH /api/notes/{id}.
type UpdateNoteRequest struct {
	Title   *string  `json:"title,omitempty"`
	Content *string  `json:"content,omitempty"`
	Summary *string  `json:"summary,omitempty"`
	Tags    []string `json:"tags,omitempty"`
}

// SearchNotes calls GET /api/notes/search.
func (c *Client) SearchNotes(query string, opts SearchOpts) (*SearchResponse, error) {
	params := url.Values{}
	params.Set("q", query)
	if opts.Mode != "" {
		params.Set("search_type", opts.Mode)
	}
	if opts.Limit > 0 {
		params.Set("limit", strconv.Itoa(opts.Limit))
	}
	if opts.Threshold > 0 {
		params.Set("threshold", strconv.FormatFloat(opts.Threshold, 'f', -1, 64))
	}
	if len(opts.Tags) > 0 {
		params.Set("tags", strings.Join(opts.Tags, ","))
	}

	var out SearchResponse
	if err := c.get("/api/notes/search?"+params.Encode(), &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// SearchOpts holds optional parameters for SearchNotes.
type SearchOpts struct {
	Mode      string   // semantic | keyword | hybrid
	Limit     int
	Threshold float64
	Tags      []string
}

// CreateNote calls POST /api/notes.
func (c *Client) CreateNote(req CreateNoteRequest) (*Note, error) {
	var out Note
	if err := c.post("/api/notes", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ListNotes calls GET /api/notes.
func (c *Client) ListNotes(opts ListOpts) ([]Note, error) {
	params := url.Values{}
	if len(opts.Tags) > 0 {
		params.Set("tags", strings.Join(opts.Tags, ","))
	}
	if opts.Sort != "" {
		params.Set("sort", opts.Sort)
	}
	if opts.Order != "" {
		params.Set("order", opts.Order)
	}
	if opts.Limit > 0 {
		params.Set("limit", strconv.Itoa(opts.Limit))
	}
	if opts.Offset > 0 {
		params.Set("offset", strconv.Itoa(opts.Offset))
	}

	var out []Note
	if err := c.get("/api/notes?"+params.Encode(), &out); err != nil {
		return nil, err
	}
	return out, nil
}

// ListOpts holds optional parameters for ListNotes.
type ListOpts struct {
	Tags   []string
	Sort   string
	Order  string
	Limit  int
	Offset int
}

// GetNote calls GET /api/notes/{id}.
func (c *Client) GetNote(id string) (*Note, error) {
	var out Note
	if err := c.get(fmt.Sprintf("/api/notes/%s", id), &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// UpdateNote calls PATCH /api/notes/{id}.
func (c *Client) UpdateNote(id string, req UpdateNoteRequest) (*Note, error) {
	var out Note
	if err := c.patch(fmt.Sprintf("/api/notes/%s", id), req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// DeleteNote calls DELETE /api/notes/{id}.
func (c *Client) DeleteNote(id string) error {
	return c.del(fmt.Sprintf("/api/notes/%s", id), nil)
}
