package client

// HealthResponse is the response from GET /api/health.
type HealthResponse struct {
	Status   string `json:"status"`
	Database string `json:"database"`
	VectorDB string `json:"vector_db"`
	Version  string `json:"version"`
}

// StatsResponse is the response from GET /api/stats.
type StatsResponse struct {
	Notes    map[string]any `json:"notes"`
	Links    map[string]any `json:"links"`
	Tags     map[string]any `json:"tags"`
	Buffer   map[string]any `json:"buffer"`
	VectorDB map[string]any `json:"vector_db"`
}

// ConfigResponse is the response from GET /api/config.
type ConfigResponse struct {
	EmbeddingProvider  string `json:"embedding_provider"`
	EmbeddingModel     string `json:"embedding_model"`
	EmbeddingDimension int    `json:"embedding_dimension"`
	EmbeddingMode      string `json:"embedding_mode"`
	BufferRetentionDays int   `json:"buffer_retention_days"`
	Debug              bool   `json:"debug"`
	Version            string `json:"version"`
}

// SyncResponse is the response from POST /api/admin/sync-embeddings.
type SyncResponse struct {
	Status       string `json:"status"`
	PendingNotes int    `json:"pending_notes"`
}

// ReembedResponse is the response from POST /api/admin/reembed.
type ReembedResponse struct {
	Status     string `json:"status"`
	TotalNotes int    `json:"total_notes"`
}

// ReembedStatusResponse is the response from GET /api/admin/reembed/status.
type ReembedStatusResponse struct {
	Status string `json:"status"`
}

// GetHealth calls GET /api/health.
func (c *Client) GetHealth() (*HealthResponse, error) {
	var out HealthResponse
	if err := c.get("/api/health", &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetStats calls GET /api/stats.
func (c *Client) GetStats() (*StatsResponse, error) {
	var out StatsResponse
	if err := c.get("/api/stats", &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetConfig calls GET /api/config.
func (c *Client) GetConfig() (*ConfigResponse, error) {
	var out ConfigResponse
	if err := c.get("/api/config", &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// SyncEmbeddings calls POST /api/admin/sync-embeddings.
func (c *Client) SyncEmbeddings() (*SyncResponse, error) {
	var out SyncResponse
	if err := c.post("/api/admin/sync-embeddings", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Reembed calls POST /api/admin/reembed.
func (c *Client) Reembed(confirm string) (*ReembedResponse, error) {
	var out ReembedResponse
	if err := c.post("/api/admin/reembed", map[string]string{"confirm": confirm}, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// GetReembedStatus calls GET /api/admin/reembed/status.
func (c *Client) GetReembedStatus() (*ReembedStatusResponse, error) {
	var out ReembedStatusResponse
	if err := c.get("/api/admin/reembed/status", &out); err != nil {
		return nil, err
	}
	return &out, nil
}
