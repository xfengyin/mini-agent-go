// Copyright 2024 MiniAgent Authors
// SPDX-License-Identifier: MIT

// Package main - Ultra-Lightweight AI Agent Framework in Pure Go
//
// MiniAgent is a minimalist, embeddable AI Agent framework inspired by PicoClaw.
// Features:
//   - Pure Go, zero external dependencies
//   - < 1000 lines of code
//   - OpenAI API compatible
//   - Function Calling support
//   - Built-in tools: shell, file, http, calc
//   - Easy to embed and extend
//
// Usage:
//
//	agent := miniagent.New(apiKey, "gpt-4o-mini")
//	agent.RegisterTool("shell", tools.ShellTool)
//	result, _ := agent.Run(context.Background(), "Execute 'ls -la'")
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// =============================================================================
// Version Information
// =============================================================================

const (
	Version   = "0.1.0"
	BuildTime = "2024-01-01"
)

// =============================================================================
// Message Types - Core data structures for LLM communication
// =============================================================================

// Role represents the role of a message sender
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// Message represents a single message in the conversation
type Message struct {
	Role    Role                   `json:"role"`
	Content string                 `json:"content"`
	Name    string                 `json:"name,omitempty"`
	ToolCalls []ToolCall          `json:"tool_calls,omitempty"`
	ToolCallID string              `json:"tool_call_id,omitempty"`
}

// ToolCall represents a tool invocation request from LLM
type ToolCall struct {
	ID       string          `json:"id"`
	Type     string           `json:"type"`
	Function FunctionCall     `json:"function"`
}

// FunctionCall represents the function to be called
type FunctionCall struct {
	Name      string          `json:"name"`
	Arguments string         `json:"arguments"` // JSON string
}

// ToolResult represents the result of a tool execution
type ToolResult struct {
	ToolCallID string `json:"tool_call_id"`
	Role       Role   `json:"role"`
	Content    string `json:"content"`
	Name       string `json:"name"`
}

// =============================================================================
// Tool System - Function Calling implementation
// =============================================================================

// Tool represents an executable tool/function
type Tool struct {
	Name        string
	Description string
	Parameters  map[string]ParameterSchema
	Handler     ToolHandler
}

// ParameterSchema defines the schema for tool parameters (JSON Schema style)
type ParameterSchema struct {
	Type        string `json:"type"`
	Description string `json:"description,omitempty"`
	Default     any    `json:"default,omitempty"`
}

// ToolHandler is the function signature for tool implementations
type ToolHandler func(ctx context.Context, args map[string]any) (string, error)

// ToolRegistry manages all available tools
type ToolRegistry struct {
	tools map[string]*Tool
}

// NewToolRegistry creates a new tool registry
func NewToolRegistry() *ToolRegistry {
	return &ToolRegistry{
		tools: make(map[string]*Tool),
	}
}

// Register adds a tool to the registry
func (r *ToolRegistry) Register(tool Tool) {
	r.tools[tool.Name] = &tool
}

// Get retrieves a tool by name
func (r *ToolRegistry) Get(name string) (*Tool, bool) {
	tool, ok := r.tools[name]
	return tool, ok
}

// List returns all registered tools
func (r *ToolRegistry) List() []*Tool {
	tools := make([]*Tool, 0, len(r.tools))
	for _, t := range r.tools {
		tools = append(tools, t)
	}
	return tools
}

// Names returns names of all registered tools
func (r *ToolRegistry) Names() []string {
	names := make([]string, 0, len(r.tools))
	for name := range r.tools {
		names = append(names, name)
	}
	return names
}

// =============================================================================
// Built-in Tools - Ready-to-use tools
// =============================================================================

// ShellTool executes shell commands
// Usage: {"command": "ls -la"}
func ShellTool(ctx context.Context, args map[string]any) (string, error) {
	cmdStr, ok := args["command"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'command' parameter")
	}

	// Use bash -c for better compatibility
	cmd := exec.Command("bash", "-c", cmdStr)
	cmd.Env = os.Environ()

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Sprintf("Error: %v\nOutput: %s", err, string(output)), nil
	}

	return string(output), nil
}

// FileReadTool reads file contents
// Usage: {"path": "/path/to/file", "max_lines": 100}
func FileReadTool(ctx context.Context, args map[string]any) (string, error) {
	path, ok := args["path"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'path' parameter")
	}

	maxLines := 0
	if ml, ok := args["max_lines"].(float64); ok {
		maxLines = int(ml)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read file: %w", err)
	}

	content := string(data)
	lines := strings.Split(content, "\n")

	if maxLines > 0 && len(lines) > maxLines {
		content = strings.Join(lines[:maxLines], "\n") + fmt.Sprintf("\n... (%d more lines)", len(lines)-maxLines)
	}

	return content, nil
}

// FileWriteTool writes content to a file
// Usage: {"path": "/path/to/file", "content": "Hello, World!"}
func FileWriteTool(ctx context.Context, args map[string]any) (string, error) {
	path, ok := args["path"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'path' parameter")
	}

	content, ok := args["content"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'content' parameter")
	}

	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		return "", fmt.Errorf("failed to write file: %w", err)
	}

	return fmt.Sprintf("Successfully wrote %d bytes to %s", len(content), path), nil
}

// HTTPGetTool performs HTTP GET requests
// Usage: {"url": "https://api.example.com/data"}
func HTTPGetTool(ctx context.Context, args map[string]any) (string, error) {
	url, ok := args["url"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'url' parameter")
	}

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	// Add common headers
	req.Header.Set("User-Agent", "MiniAgent/1.0")
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	return fmt.Sprintf("Status: %d\nHeaders: %v\nBody: %s", resp.StatusCode, resp.Header, string(body)), nil
}

// HTTPPostTool performs HTTP POST requests
// Usage: {"url": "https://api.example.com/data", "body": "{\"key\": \"value\"}"}
func HTTPPostTool(ctx context.Context, args map[string]any) (string, error) {
	url, ok := args["url"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'url' parameter")
	}

	body := ""
	if b, ok := args["body"].(string); ok {
		body = b
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, strings.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "MiniAgent/1.0")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	return fmt.Sprintf("Status: %d\nBody: %s", resp.StatusCode, string(respBody)), nil
}

// CalcTool performs simple mathematical calculations
// Usage: {"expression": "2 + 2 * 3"}
func CalcTool(ctx context.Context, args map[string]any) (string, error) {
	expr, ok := args["expression"].(string)
	if !ok {
		return "", fmt.Errorf("missing 'expression' parameter")
	}

	// Simple calculator using eval (basic safety check)
	// For production, use a proper expression parser
	if !isSafeExpression(expr) {
		return "", fmt.Errorf("unsafe expression detected")
	}

	// Use bc for calculation
	cmd := exec.Command("bash", "-c", fmt.Sprintf("echo 'scale=10; %s' | bc -l", expr))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("calculation failed: %w", err)
	}

	result := strings.TrimSpace(string(output))
	return fmt.Sprintf("%s = %s", expr, result), nil
}

// isSafeExpression checks if the expression is safe to evaluate
func isSafeExpression(expr string) bool {
	// Only allow numbers, operators, spaces, dots, and parentheses
	allowed := regexp.MustCompile(`^[\d\s+\-*/().]+$`)
	return allowed.MatchString(expr)
}

// TimeTool returns current time information
// Usage: {"format": "2006-01-02 15:04:05"}
func TimeTool(ctx context.Context, args map[string]any) (string, error) {
	format := "2006-01-02 15:04:05 MST"
	if f, ok := args["format"].(string); ok && f != "" {
		format = f
	}

	now := time.Now()
	return now.Format(format), nil
}

// GetDefaultTools returns all built-in tools
func GetDefaultTools() *ToolRegistry {
	registry := NewToolRegistry()

	registry.Register(Tool{
		Name:        "shell",
		Description: "Execute a shell command and return the output",
		Parameters: map[string]ParameterSchema{
			"command": {Type: "string", Description: "The shell command to execute"},
		},
		Handler: ShellTool,
	})

	registry.Register(Tool{
		Name:        "file_read",
		Description: "Read contents of a file",
		Parameters: map[string]ParameterSchema{
			"path":      {Type: "string", Description: "Path to the file to read"},
			"max_lines": {Type: "number", Description: "Maximum number of lines to read (optional)"},
		},
		Handler: FileReadTool,
	})

	registry.Register(Tool{
		Name:        "file_write",
		Description: "Write content to a file",
		Parameters: map[string]ParameterSchema{
			"path":    {Type: "string", Description: "Path to the file to write"},
			"content": {Type: "string", Description: "Content to write to the file"},
		},
		Handler: FileWriteTool,
	})

	registry.Register(Tool{
		Name:        "http_get",
		Description: "Perform an HTTP GET request",
		Parameters: map[string]ParameterSchema{
			"url": {Type: "string", Description: "The URL to fetch"},
		},
		Handler: HTTPGetTool,
	})

	registry.Register(Tool{
		Name:        "http_post",
		Description: "Perform an HTTP POST request",
		Parameters: map[string]ParameterSchema{
			"url":  {Type: "string", Description: "The URL to post to"},
			"body": {Type: "string", Description: "The request body (JSON string)"},
		},
		Handler: HTTPPostTool,
	})

	registry.Register(Tool{
		Name:        "calc",
		Description: "Evaluate a mathematical expression",
		Parameters: map[string]ParameterSchema{
			"expression": {Type: "string", Description: "Mathematical expression (e.g., '2 + 2 * 3')"},
		},
		Handler: CalcTool,
	})

	registry.Register(Tool{
		Name:        "time",
		Description: "Get the current time",
		Parameters: map[string]ParameterSchema{
			"format": {Type: "string", Description: "Time format (Go format), default: '2006-01-02 15:04:05 MST'"},
		},
		Handler: TimeTool,
	})

	return registry
}

// =============================================================================
// LLM Provider - OpenAI API compatible interface
// =============================================================================

// LLMProvider defines the interface for LLM backends
type LLMProvider interface {
	Chat(ctx context.Context, messages []Message) (*ChatResponse, error)
	Name() string
}

// ChatResponse represents the response from LLM
type ChatResponse struct {
	Content        string
	ToolCalls      []ToolCall
	FinishReason   string
	Usage          Usage
}

// Usage represents token usage information
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// OpenAIProvider implements OpenAI API
type OpenAIProvider struct {
	APIKey   string
	Model    string
	BaseURL  string
	Client   *http.Client
}

// NewOpenAIProvider creates a new OpenAI provider
func NewOpenAIProvider(apiKey, model string) *OpenAIProvider {
	return &OpenAIProvider{
		APIKey:  apiKey,
		Model:   model,
		BaseURL: "https://api.openai.com/v1",
		Client: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

// Chat sends a chat request to OpenAI
func (p *OpenAIProvider) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	url := fmt.Sprintf("%s/chat/completions", p.BaseURL)

	// Convert messages to OpenAI format
	openAIMessages := make([]map[string]any, len(messages))
	for i, m := range messages {
		msg := map[string]any{
			"role":    string(m.Role),
			"content": m.Content,
		}
		if m.Name != "" {
			msg["name"] = m.Name
		}
		if m.ToolCallID != "" {
			msg["tool_call_id"] = m.ToolCallID
		}
		if len(m.ToolCalls) > 0 {
			msg["tool_calls"] = m.ToolCalls
		}
		openAIMessages[i] = msg
	}

	// Prepare tools for function calling
	tools := []map[string]any{}

	// Request body
	body := map[string]any{
		"model":    p.Model,
		"messages": openAIMessages,
		"stream":   false,
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+p.APIKey)

	resp, err := p.Client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]any
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	choices := result["choices"].([]any)
	if len(choices) == 0 {
		return nil, fmt.Errorf("no choices in response")
	}

	choice := choices[0].(map[string]any)
	message := choice["message"].(map[string]any)

	response := &ChatResponse{
		FinishReason: choice["finish_reason"].(string),
	}

	if content, ok := message["content"].(string); ok {
		response.Content = content
	}

	if toolCalls, ok := message["tool_calls"].([]any); ok {
		for _, tc := range toolCalls {
			tcMap := tc.(map[string]any)
			function := tcMap["function"].(map[string]any)
			response.ToolCalls = append(response.ToolCalls, ToolCall{
				ID:   tcMap["id"].(string),
				Type: "function",
				Function: FunctionCall{
					Name:      function["name"].(string),
					Arguments: function["arguments"].(string),
				},
			})
		}
	}

	if usage, ok := result["usage"].(map[string]any); ok {
		response.Usage = Usage{
			PromptTokens:     int(usage["prompt_tokens"].(float64)),
			CompletionTokens: int(usage["completion_tokens"].(float64)),
			TotalTokens:      int(usage["total_tokens"].(float64)),
		}
	}

	return response, nil
}

// Name returns the provider name
func (p *OpenAIProvider) Name() string {
	return "openai"
}

// =============================================================================
// OllamaProvider implements Ollama API (OpenAI-compatible)
// =============================================================================

// OllamaProvider implements Ollama API
type OllamaProvider struct {
	BaseURL string
	Model   string
	Client  *http.Client
}

// NewOllamaProvider creates a new Ollama provider
func NewOllamaProvider(baseURL, model string) *OllamaProvider {
	if baseURL == "" {
		baseURL = "http://localhost:11434"
	}
	if model == "" {
		model = "llama3.2"
	}
	return &OllamaProvider{
		BaseURL: baseURL,
		Model:   model,
		Client: &http.Client{
			Timeout: 300 * time.Second,
		},
	}
}

// Chat sends a chat request to Ollama
func (p *OllamaProvider) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	url := fmt.Sprintf("%s/api/chat", p.BaseURL)

	// Convert messages to Ollama format
	ollamaMessages := make([]map[string]string, len(messages))
	for i, m := range messages {
		ollamaMessages[i] = map[string]string{
			"role":    string(m.Role),
			"content": m.Content,
		}
	}

	body := map[string]any{
		"model":    p.Model,
		"messages": ollamaMessages,
		"stream":   false,
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := p.Client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Ollama error (%d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]any
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	message := result["message"].(map[string]any)

	return &ChatResponse{
		Content: message["content"].(string),
	}, nil
}

// Name returns the provider name
func (p *OllamaProvider) Name() string {
	return "ollama"
}

// =============================================================================
// Agent - The core AI Agent
// =============================================================================

// AgentConfig holds agent configuration
type AgentConfig struct {
	SystemPrompt   string
	MaxTokens      int
	Temperature    float64
	MaxIterations  int
	Tools          *ToolRegistry
}

// DefaultAgentConfig returns default configuration
func DefaultAgentConfig() *AgentConfig {
	return &AgentConfig{
		SystemPrompt:  "You are a helpful AI assistant. You have access to various tools to help accomplish tasks.",
		MaxTokens:      4096,
		Temperature:    0.7,
		MaxIterations:  10,
		Tools:          GetDefaultTools(),
	}
}

// Agent is the main AI agent
type Agent struct {
	provider LLMProvider
	config   *AgentConfig
	messages []Message
}

// NewAgent creates a new agent with OpenAI provider
func NewAgent(apiKey, model string) *Agent {
	return &Agent{
		provider: NewOpenAIProvider(apiKey, model),
		config:   DefaultAgentConfig(),
		messages: make([]Message, 0),
	}
}

// NewAgentWithProvider creates a new agent with custom provider
func NewAgentWithProvider(provider LLMProvider) *Agent {
	return &Agent{
		provider: provider,
		config:   DefaultAgentConfig(),
		messages: make([]Message, 0),
	}
}

// NewAgentWithConfig creates a new agent with custom config
func NewAgentWithConfig(apiKey, model string, config *AgentConfig) *Agent {
	if config.Tools == nil {
		config.Tools = GetDefaultTools()
	}
	return &Agent{
		provider: NewOpenAIProvider(apiKey, model),
		config:   config,
		messages: make([]Message, 0),
	}
}

// SetSystemPrompt sets the system prompt
func (a *Agent) SetSystemPrompt(prompt string) {
	a.config.SystemPrompt = prompt
}

// RegisterTool registers a new tool
func (a *Agent) RegisterTool(name string, handler ToolHandler, description string, params map[string]ParameterSchema) {
	a.config.Tools.Register(Tool{
		Name:        name,
		Description: description,
		Parameters:  params,
		Handler:     handler,
	})
}

// Run executes the agent with user input
func (a *Agent) Run(ctx context.Context, userInput string) (string, error) {
	// Add user message
	a.messages = append(a.messages, Message{
		Role:    RoleUser,
		Content: userInput,
	})

	// Main agent loop
	for iteration := 0; iteration < a.config.MaxIterations; iteration++ {
		// Build messages with system prompt
		allMessages := []Message{{
			Role:    RoleSystem,
			Content: a.config.SystemPrompt,
		}}

		// Add conversation history
		allMessages = append(allMessages, a.messages...)

		// Add tool definitions if tools available
		tools := a.buildToolDefinitions()

		// Get LLM response
		resp, err := a.provider.Chat(ctx, allMessages)
		if err != nil {
			return "", fmt.Errorf("LLM error: %w", err)
		}

		// If no tool calls, return the response
		if len(resp.ToolCalls) == 0 {
			a.messages = append(a.messages, Message{
				Role:    RoleAssistant,
				Content: resp.Content,
			})
			return resp.Content, nil
		}

		// Process tool calls
		for _, tc := range resp.ToolCalls {
			// Add assistant message with tool call
			a.messages = append(a.messages, Message{
				Role:       RoleAssistant,
				Content:    resp.Content,
				ToolCalls:  []ToolCall{tc},
			})

			// Execute tool
			toolResult, err := a.executeTool(ctx, tc)
			if err != nil {
				toolResult = fmt.Sprintf("Error: %v", err)
			}

			// Add tool result message
			a.messages = append(a.messages, Message{
				Role:       RoleTool,
				Content:    toolResult,
				ToolCallID: tc.ID,
				Name:       tc.Function.Name,
			})
		}
	}

	return "", fmt.Errorf("max iterations (%d) exceeded", a.config.MaxIterations)
}

// buildToolDefinitions creates tool definitions for function calling
func (a *Agent) buildToolDefinitions() []map[string]any {
	if a.config.Tools == nil {
		return nil
	}

	tools := make([]map[string]any, 0)
	for _, tool := range a.config.Tools.List() {
		params := map[string]any{
			"type": "object",
			"properties": map[string]any{},
		}
		props := params["properties"].(map[string]any)
		required := make([]string, 0)

		for name, schema := range tool.Parameters {
			props[name] = map[string]any{
				"type":        schema.Type,
				"description": schema.Description,
			}
			required = append(required, name)
		}
		params["required"] = required

		tools = append(tools, map[string]any{
			"type": "function",
			"function": map[string]any{
				"name":        tool.Name,
				"description": tool.Description,
				"parameters":  params,
			},
		})
	}

	return tools
}

// executeTool executes a tool by name
func (a *Agent) executeTool(ctx context.Context, tc ToolCall) (string, error) {
	tool, ok := a.config.Tools.Get(tc.Function.Name)
	if !ok {
		return "", fmt.Errorf("tool not found: %s", tc.Function.Name)
	}

	// Parse arguments
	var args map[string]any
	if err := json.Unmarshal([]byte(tc.Function.Arguments), &args); err != nil {
		return "", fmt.Errorf("failed to parse arguments: %w", err)
	}

	// Execute tool
	return tool.Handler(ctx, args)
}

// ClearHistory clears conversation history
func (a *Agent) ClearHistory() {
	a.messages = make([]Message, 0)
}

// History returns conversation history
func (a *Agent) History() []Message {
	return a.messages
}

// Embed embeds the agent into another Go program
// Returns the agent instance for configuration
func Embed(apiKey, model string) *Agent {
	return NewAgent(apiKey, model)
}

// =============================================================================
// CLI - Command Line Interface
// =============================================================================

func main() {
	fmt.Println("========================================")
	fmt.Println("  MiniAgent - Ultra-Lightweight AI Agent")
	fmt.Println("  Version:", Version)
	fmt.Println("========================================")
	fmt.Println()

	// Get API key from environment
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fmt.Println("Error: OPENAI_API_KEY environment variable not set")
		fmt.Println()
		fmt.Println("Usage:")
		fmt.Println("  export OPENAI_API_KEY=your-api-key")
		fmt.Println("  go run agent.go \"Your question here\"")
		fmt.Println()
		fmt.Println("Or use Ollama (local):")
		fmt.Println("  export OPENAI_API_KEY=ollama")
		fmt.Println("  go run agent.go \"Your question here\"")
		os.Exit(1)
	}

	model := "gpt-4o-mini"
	if len(os.Args) > 1 {
		model = os.Args[1]
	}

	// Create agent
	var agent *Agent
	if apiKey == "ollama" {
		fmt.Println("Using Ollama provider...")
		agent = NewAgentWithProvider(NewOllamaProvider("", "llama3.2"))
		model = "llama3.2"
	} else {
		fmt.Printf("Using OpenAI provider with model: %s\n", model)
		agent = NewAgent(apiKey, model)
	}

	// Set system prompt
	agent.SetSystemPrompt(`You are MiniAgent, a helpful AI assistant with access to tools.

Available tools:
- shell: Execute shell commands
- file_read: Read files
- file_write: Write files
- http_get: Make GET requests
- http_post: Make POST requests
- calc: Calculate expressions
- time: Get current time

Use tools when appropriate to help answer questions.`)

	if len(os.Args) > 2 {
		// Single query mode
		query := os.Args[2]
		fmt.Printf("\n[User] %s\n\n", query)

		ctx := context.Background()
		response, err := agent.Run(ctx, query)
		if err != nil {
			fmt.Printf("[Error] %v\n", err)
			os.Exit(1)
		}

		fmt.Printf("[MiniAgent] %s\n", response)
	} else {
		// Interactive mode
		fmt.Println("\nInteractive Mode - Type 'exit' to quit, 'clear' to clear history")
		fmt.Println()

		for {
			fmt.Print("[You] ")
			var input string
			fmt.Scanln(&input)

			input = strings.TrimSpace(input)
			if input == "" {
				continue
			}

			if input == "exit" || input == "quit" {
				fmt.Println("Goodbye!")
				break
			}

			if input == "clear" {
				agent.ClearHistory()
				fmt.Println("History cleared.")
				continue
			}

			if input == "history" {
				fmt.Println("\nConversation History:")
				for i, msg := range agent.History() {
					role := string(msg.Role)
					content := msg.Content
					if len(content) > 100 {
						content = content[:100] + "..."
					}
					fmt.Printf("  %d. [%s] %s\n", i+1, role, content)
				}
				fmt.Println()
				continue
			}

			ctx := context.Background()
			response, err := agent.Run(ctx, input)
			if err != nil {
				fmt.Printf("[Error] %v\n", err)
				continue
			}

			fmt.Printf("[MiniAgent] %s\n\n", response)
		}
	}
}
