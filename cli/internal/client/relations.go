package client

import "fmt"

// RelationType represents a relation type from the API.
type RelationType struct {
	ID              string `json:"id"`
	Name            string `json:"name"`
	Description     string `json:"description,omitempty"`
	IsBidirectional bool   `json:"is_bidirectional"`
	LinkCount       int    `json:"link_count"`
	CreatedAt       string `json:"created_at"`
}

// CreateRelationRequest is the request body for POST /api/relations.
type CreateRelationRequest struct {
	Name            string `json:"name"`
	Description     string `json:"description,omitempty"`
	IsBidirectional bool   `json:"is_bidirectional,omitempty"`
}

// UpdateRelationRequest is the request body for PUT /api/relations/{id}.
type UpdateRelationRequest struct {
	Name            *string `json:"name,omitempty"`
	Description     *string `json:"description,omitempty"`
	IsBidirectional *bool   `json:"is_bidirectional,omitempty"`
}

// ListRelations calls GET /api/relations.
func (c *Client) ListRelations() ([]RelationType, error) {
	var out []RelationType
	if err := c.get("/api/relations", &out); err != nil {
		return nil, err
	}
	return out, nil
}

// CreateRelation calls POST /api/relations.
func (c *Client) CreateRelation(req CreateRelationRequest) (*RelationType, error) {
	var out RelationType
	if err := c.post("/api/relations", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetRelation calls GET /api/relations/{id}.
func (c *Client) GetRelation(id string) (*RelationType, error) {
	var out RelationType
	if err := c.get(fmt.Sprintf("/api/relations/%s", id), &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// UpdateRelation calls PUT /api/relations/{id}.
func (c *Client) UpdateRelation(id string, req UpdateRelationRequest) (*RelationType, error) {
	var out RelationType
	if err := c.do("PUT", fmt.Sprintf("/api/relations/%s", id), req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// DeleteRelation calls DELETE /api/relations/{id}.
func (c *Client) DeleteRelation(id string) error {
	return c.del(fmt.Sprintf("/api/relations/%s", id), nil)
}
