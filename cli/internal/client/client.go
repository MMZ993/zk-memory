package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"
)

// Client is the base HTTP client for the memory API.
type Client struct {
	baseURL    string
	apiKey     string
	httpClient *http.Client
}

// New creates a Client from environment variables.
// MEMORY_API_URL is required. MEMORY_API_KEY and MEMORY_TIMEOUT are optional.
func New() (*Client, error) {
	baseURL := os.Getenv("MEMORY_API_URL")
	if baseURL == "" {
		return nil, fmt.Errorf("MEMORY_API_URL is required")
	}

	timeout := 30 * time.Second
	if s := os.Getenv("MEMORY_TIMEOUT"); s != "" {
		secs, err := strconv.Atoi(s)
		if err != nil {
			return nil, fmt.Errorf("MEMORY_TIMEOUT must be an integer: %w", err)
		}
		timeout = time.Duration(secs) * time.Second
	}

	return &Client{
		baseURL: baseURL,
		apiKey:  os.Getenv("MEMORY_API_KEY"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}, nil
}

// APIError represents an error response from the API.
type APIError struct {
	StatusCode int
	Body       string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("API error %d: %s", e.StatusCode, e.Body)
}

// do executes an HTTP request and decodes the JSON response into out.
// If out is nil the response body is discarded.
func (c *Client) do(method, path string, body any, out any) error {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequest(method, c.baseURL+path, bodyReader)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("X-API-Key", c.apiKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return &APIError{StatusCode: resp.StatusCode, Body: string(respBody)}
	}

	if out != nil {
		if err := json.Unmarshal(respBody, out); err != nil {
			return fmt.Errorf("decode response: %w", err)
		}
	}
	return nil
}

// get is a convenience wrapper for GET requests.
func (c *Client) get(path string, out any) error {
	return c.do(http.MethodGet, path, nil, out)
}

// post is a convenience wrapper for POST requests.
func (c *Client) post(path string, body, out any) error {
	return c.do(http.MethodPost, path, body, out)
}

// patch is a convenience wrapper for PATCH requests.
func (c *Client) patch(path string, body, out any) error {
	return c.do(http.MethodPatch, path, body, out)
}

// del is a convenience wrapper for DELETE requests.
func (c *Client) del(path string, out any) error {
	return c.do(http.MethodDelete, path, nil, out)
}
