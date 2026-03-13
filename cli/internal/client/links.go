package client

import (
	"fmt"
	"net/url"
	"strconv"
)

// RelationTypeSummary is the embedded relation type in a NoteLink.
type RelationTypeSummary struct {
	ID              string `json:"id"`
	Name            string `json:"name"`
	Description     string `json:"description,omitempty"`
	IsBidirectional bool   `json:"is_bidirectional"`
}

// NoteLink is the full link object returned by the links API.
type NoteLink struct {
	ID             string              `json:"id"`
	SourceID       string              `json:"source_id"`
	TargetID       string              `json:"target_id"`
	RelationTypeID string              `json:"relation_type_id"`
	RelationType   RelationTypeSummary `json:"relation_type"`
	Description    string              `json:"description,omitempty"`
	CreatedAt      string              `json:"created_at"`
}

// CreateLinkRequest is the request body for POST /api/notes/links.
type CreateLinkRequest struct {
	SourceID     string `json:"source_id"`
	TargetID     string `json:"target_id"`
	RelationType string `json:"relation_type"`
	Description  string `json:"description,omitempty"`
}

// NoteLinkListOpts holds optional parameters for GetNoteLinks.
type NoteLinkListOpts struct {
	Direction string // incoming | outgoing | all
	Limit     int
}

// GetNoteLinks calls GET /api/notes/{id}/links.
func (c *Client) GetNoteLinks(noteID string, opts NoteLinkListOpts) ([]NoteLink, error) {
	params := url.Values{}
	if opts.Direction != "" {
		params.Set("direction", opts.Direction)
	}
	if opts.Limit > 0 {
		params.Set("limit", strconv.Itoa(opts.Limit))
	}
	var out []NoteLink
	if err := c.get(fmt.Sprintf("/api/notes/%s/links?%s", noteID, params.Encode()), &out); err != nil {
		return nil, err
	}
	return out, nil
}

// CreateLink calls POST /api/notes/links.
func (c *Client) CreateLink(req CreateLinkRequest) (*NoteLink, error) {
	var out NoteLink
	if err := c.post("/api/notes/links", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// DeleteLink calls DELETE /api/notes/links/{id}.
func (c *Client) DeleteLink(linkID string) error {
	return c.del(fmt.Sprintf("/api/notes/links/%s", linkID), nil)
}

// GetNoteGraph calls GET /api/notes/{id}/graph.
func (c *Client) GetNoteGraph(noteID string, depth int) (*SearchResponse, error) {
	params := url.Values{}
	if depth > 0 {
		params.Set("depth", strconv.Itoa(depth))
	}
	var out SearchResponse
	if err := c.get(fmt.Sprintf("/api/notes/%s/graph?%s", noteID, params.Encode()), &out); err != nil {
		return nil, err
	}
	return &out, nil
}
