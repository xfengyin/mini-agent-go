# MiniAgent - Ultra-Lightweight AI Agent Framework

<p align="center">
  <img src="assets/logo.svg" alt="MiniAgent" width="256">
</p>

<p align="center">
  <strong>Pure Go</strong> · <strong>&lt;1000 lines</strong> · <strong>Zero dependencies</strong> · <strong>Embeddable</strong>
</p>

<p align="center">
  <a href="https://github.com/xfengyin/mini-agent-go">
    <img src="https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go" alt="Go">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Lines-1000-blue" alt="Lines">
</p>

---

**MiniAgent** is an ultra-lightweight AI Agent framework written in pure Go. Inspired by [PicoClaw](https://github.com/sipeed/picoclaw), it provides a minimalist, embeddable solution for building AI-powered applications.

> **$0 Hardware** · **<10MB** · **ms Boot** · **Function Calling**

## Features

| Feature | Description |
|---------|-------------|
| ⚡ **Minimalist** | ~1000 lines of clean Go code |
| 🔌 **Zero Dependencies** | Pure Go, no external packages |
| 🔧 **Function Calling** | OpenAI-style tool calling |
| 🔄 **Embeddable** | Easy to integrate into any Go project |
| 🛠️ **Built-in Tools** | Shell, File, HTTP, Calc, Time |
| 🌐 **Multi-Provider** | OpenAI API, Ollama, custom providers |

## Quick Start

### Installation

```bash
go get github.com/xfengyin/mini-agent-go
```

### Basic Usage

```go
package main

import (
    "context"
    "fmt"
    "github.com/xfengyin/mini-agent-go"
)

func main() {
    // Create agent
    agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")
    
    // Run query
    ctx := context.Background()
    response, err := agent.Run(ctx, "Hello, how are you?")
    if err != nil {
        panic(err)
    }
    
    fmt.Println(response)
}
```

### With Custom Tools

```go
agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

// Register custom tool
agent.RegisterTool(
    "weather",
    func(ctx context.Context, args map[string]any) (string, error) {
        city := args["city"].(string)
        return fmt.Sprintf("Weather in %s: Sunny, 25°C", city), nil
    },
    "Get weather information for a city",
    map[string]miniagent.ParameterSchema{
        "city": {Type: "string", Description: "City name"},
    },
)
```

## CLI Usage

```bash
# Set API key
export OPENAI_API_KEY=your-api-key

# Single query
go run agent.go "What is 2 + 2?"

# Interactive mode
go run agent.go
```

### With Ollama (Local)

```bash
export OPENAI_API_KEY=ollama
go run agent.go
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      MiniAgent                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Agent     │  │  LLM        │  │   Tools     │     │
│  │   Core      │──│  Provider   │──│   Registry  │     │
│  │             │  │  (OpenAI/   │  │  (shell,    │     │
│  │  - Messages │  │   Ollama)   │  │   file,     │     │
│  │  - History  │  │             │  │   http...)  │     │
│  │  - Config   │  └─────────────┘  └─────────────┘     │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

## Built-in Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `shell` | Execute shell commands | `command: string` |
| `file_read` | Read file contents | `path: string`, `max_lines?: number` |
| `file_write` | Write to file | `path: string`, `content: string` |
| `http_get` | HTTP GET request | `url: string` |
| `http_post` | HTTP POST request | `url: string`, `body?: string` |
| `calc` | Calculate expression | `expression: string` |
| `time` | Get current time | `format?: string` |

## Embedding Example

```go
// Create embeddable agent
agent := miniagent.Embed("your-api-key", "gpt-4o-mini")

// Configure
agent.SetSystemPrompt("You are a specialized coding assistant.")
agent.RegisterTool("git_commit", gitCommitTool, "Create a git commit", nil)

// Use
response, _ := agent.Run(ctx, "Commit my changes with message 'fix bug'")
```

## Configuration

```go
config := &miniagent.AgentConfig{
    SystemPrompt: "You are a helpful assistant.",
    MaxTokens:    4096,
    Temperature:   0.7,
    MaxIterations: 10,        // Max tool call iterations
    Tools:         miniagent.GetDefaultTools(),
}

agent := miniagent.NewAgentWithConfig("api-key", "gpt-4o-mini", config)
```

## Custom LLM Provider

```go
type MyProvider struct{}

func (p *MyProvider) Chat(ctx context.Context, messages []miniagent.Message) (*miniagent.ChatResponse, error) {
    // Your implementation
    return &miniagent.ChatResponse{
        Content: "Response from my provider",
    }, nil
}

func (p *MyProvider) Name() string {
    return "my-provider"
}

agent := miniagent.NewAgentWithProvider(&MyProvider{})
```

## Comparison

| Feature | MiniAgent | LangChain | Other Frameworks |
|---------|-----------|-----------|------------------|
| Lines of Code | ~1000 | 50000+ | 10000+ |
| Dependencies | 0 | 50+ | 20+ |
| Embeddable | ✅ | ❌ | ⚠️ |
| Function Calling | ✅ | ✅ | ✅ |
| Learning Curve | Low | High | Medium |

## License

MIT License - see [LICENSE](LICENSE) for details.
