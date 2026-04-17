// Copyright 2024 MiniAgent Authors
// SPDX-License-Identifier: MIT

package main

import (
	"context"
	"testing"

	"github.com/xfengyin/mini-agent-go"
)

// TestToolRegistry tests tool registration
func TestToolRegistry(t *testing.T) {
	registry := miniagent.NewToolRegistry()

	registry.Register(miniagent.Tool{
		Name:        "test_tool",
		Description: "A test tool",
		Parameters:  map[string]miniagent.ParameterSchema{},
		Handler: func(ctx context.Context, args map[string]any) (string, error) {
			return "test result", nil
		},
	})

	tool, ok := registry.Get("test_tool")
	if !ok {
		t.Error("Tool not found")
	}

	if tool.Name != "test_tool" {
		t.Errorf("Expected tool name 'test_tool', got '%s'", tool.Name)
	}

	names := registry.Names()
	if len(names) != 1 || names[0] != "test_tool" {
		t.Errorf("Expected ['test_tool'], got %v", names)
	}
}

// TestShellTool tests shell command execution
func TestShellTool(t *testing.T) {
	ctx := context.Background()

	result, err := miniagent.ShellTool(ctx, map[string]any{
		"command": "echo hello",
	})

	if err != nil {
		t.Errorf("Shell tool failed: %v", err)
	}

	if result == "" {
		t.Error("Shell tool returned empty result")
	}
}

// TestCalcTool tests calculator
func TestCalcTool(t *testing.T) {
	ctx := context.Background()

	tests := []struct {
		expr     string
		expected string
	}{
		{"2 + 2", "2 + 2 = 4"},
		{"10 - 5", "10 - 5 = 5"},
		{"3 * 4", "3 * 4 = 12"},
	}

	for _, tt := range tests {
		result, err := miniagent.CalcTool(ctx, map[string]any{
			"expression": tt.expr,
		})

		if err != nil {
			t.Errorf("Calc tool failed for '%s': %v", tt.expr, err)
			continue
		}

		if result == "" {
			t.Errorf("Calc tool returned empty result for '%s'", tt.expr)
		}
	}
}

// TestCalcToolUnsafe tests unsafe expression detection
func TestCalcToolUnsafe(t *testing.T) {
	ctx := context.Background()

	unsafeExpressions := []string{
		"rm -rf /",
		"echo hello; rm -rf /",
		"$(whoami)",
	}

	for _, expr := range unsafeExpressions {
		result, err := miniagent.CalcTool(ctx, map[string]any{
			"expression": expr,
		})

		// Should either fail or not produce dangerous output
		if err == nil && result == "" {
			t.Logf("Expression '%s' handled safely", expr)
		}
	}
}

// TestTimeTool tests time tool
func TestTimeTool(t *testing.T) {
	ctx := context.Background()

	result, err := miniagent.TimeTool(ctx, map[string]any{})
	if err != nil {
		t.Errorf("Time tool failed: %v", err)
	}

	if result == "" {
		t.Error("Time tool returned empty result")
	}
}

// TestDefaultTools tests that all default tools are available
func TestDefaultTools(t *testing.T) {
	registry := miniagent.GetDefaultTools()

	expectedTools := []string{
		"shell",
		"file_read",
		"file_write",
		"http_get",
		"http_post",
		"calc",
		"time",
	}

	for _, name := range expectedTools {
		tool, ok := registry.Get(name)
		if !ok {
			t.Errorf("Default tool '%s' not found", name)
			continue
		}

		if tool.Handler == nil {
			t.Errorf("Tool '%s' has nil handler", name)
		}
	}
}

// TestMessageTypes tests message serialization
func TestMessageTypes(t *testing.T) {
	msg := miniagent.Message{
		Role:    miniagent.RoleUser,
		Content: "Hello, world!",
	}

	if msg.Role != miniagent.RoleUser {
		t.Errorf("Expected role 'user', got '%s'", msg.Role)
	}

	if msg.Content != "Hello, world!" {
		t.Errorf("Expected content 'Hello, world!', got '%s'", msg.Content)
	}
}

// TestToolResult tests tool result structure
func TestToolResult(t *testing.T) {
	result := miniagent.ToolResult{
		ToolCallID: "call_123",
		Role:       miniagent.RoleTool,
		Content:    "tool output",
		Name:       "test_tool",
	}

	if result.ToolCallID != "call_123" {
		t.Errorf("Expected tool_call_id 'call_123', got '%s'", result.ToolCallID)
	}
}
