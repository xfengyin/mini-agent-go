// Copyright 2024 MiniAgent Authors
// SPDX-License-Identifier: MIT

// Package examples demonstrates various MiniAgent use cases
package examples

import (
	"context"
	"fmt"

	"github.com/xfengyin/mini-agent-go"
)

// ExampleBasic demonstrates basic agent usage
func ExampleBasic() {
	agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

	ctx := context.Background()
	response, err := agent.Run(ctx, "What is the capital of France?")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Println(response)
}

// ExampleWithTools demonstrates agent with custom tools
func ExampleWithTools() {
	agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

	// Register a custom weather tool
	agent.RegisterTool(
		"weather",
		func(ctx context.Context, args map[string]any) (string, error) {
			city, ok := args["city"].(string)
			if !ok {
				return "", fmt.Errorf("city parameter required")
			}
			return fmt.Sprintf("Weather in %s: Sunny, 25°C", city), nil
		},
		"Get weather for a city",
		map[string]miniagent.ParameterSchema{
			"city": {
				Type:        "string",
				Description: "City name",
			},
		},
	)

	ctx := context.Background()
	response, err := agent.Run(ctx, "What's the weather in Tokyo?")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Println(response)
}

// ExampleShell demonstrates shell command execution
func ExampleShell() {
	agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

	ctx := context.Background()
	response, err := agent.Run(ctx, "Run 'echo Hello World' and show me the output")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Println(response)
}

// ExampleFile demonstrates file operations
func ExampleFile() {
	agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

	ctx := context.Background()

	// Read a file
	response, err := agent.Run(ctx, "Read the contents of /etc/hostname")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Println("File contents:", response)
}

// ExampleOllama demonstrates Ollama provider usage
func ExampleOllama() {
	// Create Ollama provider
	provider := miniagent.NewOllamaProvider("http://localhost:11434", "llama3.2")
	agent := miniagent.NewAgentWithProvider(provider)

	ctx := context.Background()
	response, err := agent.Run(ctx, "Hello!")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Println(response)
}

// ExampleEmbed demonstrates embedding the agent
func ExampleEmbed() {
	// Create embeddable agent
	agent := miniagent.Embed("your-api-key", "gpt-4o-mini")

	// Configure
	agent.SetSystemPrompt("You are a coding assistant that helps write Go code.")

	// Use
	ctx := context.Background()
	response, _ := agent.Run(ctx, "Write a hello world function in Go")
	fmt.Println(response)
}
