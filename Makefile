# Copyright 2024 MiniAgent Authors
# SPDX-License-Identifier: MIT

.PHONY: build test clean run example

# Build the CLI
build:
	go build -o bin/mini-agent agent.go

# Run tests
test:
	go test -v ./...

# Run the agent
run:
	go run agent.go

# Run with OpenAI
run-openai:
	export OPENAI_API_KEY=your-api-key
	go run agent.go gpt-4o-mini "Hello!"

# Run with Ollama
run-ollama:
	export OPENAI_API_KEY=ollama
	go run agent.go

# Clean build artifacts
clean:
	rm -rf bin/
	go clean

# Format code
fmt:
	go fmt ./...

# Lint code
lint:
	golangci-lint run || echo "Install: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"

# Generate documentation
docs:
	godoc -http=:8080

# Build for multiple platforms
build-all:
	GOOS=linux GOARCH=amd64 go build -o bin/mini-agent-linux-amd64 agent.go
	GOOS=linux GOARCH=arm64 go build -o bin/mini-agent-linux-arm64 agent.go
	GOOS=darwin GOARCH=amd64 go build -o bin/mini-agent-darwin-amd64 agent.go
	GOOS=darwin GOARCH=arm64 go build -o bin/mini-agent-darwin-arm64 agent.go
	GOOS=windows GOARCH=amd64 go build -o bin/mini-agent.exe agent.go
	@echo "Builds complete!"
	@ls -la bin/

# Help
help:
	@echo "MiniAgent Build System"
	@echo ""
	@echo "Targets:"
	@echo "  build        - Build CLI binary"
	@echo "  test         - Run tests"
	@echo "  run          - Run in interactive mode"
	@echo "  run-openai   - Run with OpenAI"
	@echo "  run-ollama   - Run with Ollama"
	@echo "  clean        - Clean artifacts"
	@echo "  fmt          - Format code"
	@echo "  lint         - Lint code"
	@echo "  build-all    - Cross-platform builds"
