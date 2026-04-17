# MiniAgent AI Collaboration Guide

This document helps AI assistants understand and contribute to the MiniAgent project.

## Project Overview

**MiniAgent** is an ultra-lightweight AI Agent framework written in pure Go (~1000 lines). Inspired by PicoClaw.

## Core Concepts

### Agent
The main `Agent` struct manages:
- LLM provider
- Conversation history (messages)
- Configuration (system prompt, max tokens, etc.)
- Tool registry

### Messages
Three roles:
- `system` - System prompt
- `user` - User input
- `assistant` - LLM response
- `tool` - Tool execution result

### Tools
Tools are functions the LLM can call:
- Registered with `agent.RegisterTool()`
- Have name, description, parameters
- Handler function: `func(ctx context.Context, args map[string]any) (string, error)`

### LLM Provider
Interface for different LLM backends:
- `Chat(ctx, messages) -> ChatResponse`
- Built-in: OpenAI, Ollama

## Adding a New Tool

```go
agent.RegisterTool(
    "my_tool",                    // Tool name
    func(ctx context.Context, args map[string]any) (string, error) {
        // Tool implementation
        return "result", nil
    },
    "Description of the tool",    // Human-readable description
    map[string]ParameterSchema{   // JSON Schema for parameters
        "param1": {Type: "string", Description: "..."},
    },
)
```

## Adding a New LLM Provider

Implement the `LLMProvider` interface:

```go
type MyProvider struct{}

func (p *MyProvider) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
    // Your API call logic
    return &ChatResponse{
        Content: "response text",
    }, nil
}

func (p *MyProvider) Name() string {
    return "my-provider"
}
```

## Key Files

- `agent.go` - Main framework (single file, ~1000 lines)
- `examples/examples.go` - Usage examples
- `agent_test.go` - Tests

## Building

```bash
make build      # Build CLI
make test       # Run tests
make run        # Run interactively
make fmt        # Format code
```

## Design Philosophy

1. **Minimalism** - Keep code simple and readable
2. **Zero Dependencies** - Pure Go standard library
3. **Embeddable** - Easy to integrate into other projects
4. **Extensible** - Easy to add tools and providers

## Important Notes

1. All tools receive `map[string]any` for arguments
2. Tools return `(string, error)` - result or error
3. Max iterations prevents infinite loops
4. History is maintained for context
