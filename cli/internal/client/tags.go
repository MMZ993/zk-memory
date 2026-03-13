package client

import (
	"fmt"
	"net/url"
	"strconv"
)

// Tag represents a tag from the API.
type Tag struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	NoteCount int    `json:"note_count"`
	CreatedAt string `json:"created_at"`
}

// TagListOpts holds optional parameters for ListTags.
type TagListOpts struct {
	Limit  int
	Offset int
}

// ListTags calls GET /api/tags.
func (c *Client) ListTags(opts TagListOpts) ([]Tag, error) {
	params := url.Values{}
	if opts.Limit > 0 {
		params.Set("limit", strconv.Itoa(opts.Limit))
	}
	if opts.Offset > 0 {
		params.Set("offset", strconv.Itoa(opts.Offset))
	}
	var out []Tag
	if err := c.get("/api/tags?"+params.Encode(), &out); err != nil {
		return nil, err
	}
	return out, nil
}

// CreateTag calls POST /api/tags.
func (c *Client) CreateTag(name string) (*Tag, error) {
	var out Tag
	if err := c.post("/api/tags", map[string]string{"name": name}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetNoteTags calls GET /api/notes/{id}/tags.
func (c *Client) GetNoteTags(noteID string) ([]Tag, error) {
	var out []Tag
	if err := c.get(fmt.Sprintf("/api/notes/%s/tags", noteID), &out); err != nil {
		return nil, err
	}
	return out, nil
}

// AddNoteTag calls POST /api/notes/{id}/tags.
func (c *Client) AddNoteTag(noteID, name string) (*Tag, error) {
	var out Tag
	if err := c.post(fmt.Sprintf("/api/notes/%s/tags", noteID), map[string]string{"name": name}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// RemoveNoteTag calls DELETE /api/notes/{id}/tags/{tag_id}.
func (c *Client) RemoveNoteTag(noteID, tagID string) error {
	return c.del(fmt.Sprintf("/api/notes/%s/tags/%s", noteID, tagID), nil)
}
