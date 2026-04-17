# MiniAgent - 超轻量级 AI Agent 框架

<p align="center">
  <strong>纯 Go 语言</strong> · <strong>&lt;1000 行代码</strong> · <strong>零依赖</strong> · <strong>可嵌入</strong>
</p>

---

**MiniAgent** 是一款用纯 Go 语言编写的超轻量级 AI Agent 框架。灵感来自 [PicoClaw](https://github.com/sipeed/picoclaw)，提供极简、可嵌入的 AI 应用解决方案。

> **零硬件成本** · **&lt;10MB** · **毫秒级启动** · **Function Calling**

## 特性

| 特性 | 描述 |
|------|------|
| ⚡ **极简** | ~1000 行简洁 Go 代码 |
| 🔌 **零依赖** | 纯 Go，无外部包 |
| 🔧 **Function Calling** | OpenAI 风格的工具调用 |
| 🔄 **可嵌入** | 易于集成到任何 Go 项目 |
| 🛠️ **内置工具** | Shell、文件、HTTP、计算、时间 |
| 🌐 **多 Provider** | OpenAI API、Ollama、自定义 Provider |

## 快速开始

### 安装

```bash
go get github.com/xfengyin/mini-agent-go
```

### 基本用法

```go
package main

import (
    "context"
    "fmt"
    "github.com/xfengyin/mini-agent-go"
)

func main() {
    // 创建 Agent
    agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")
    
    // 运行查询
    ctx := context.Background()
    response, err := agent.Run(ctx, "你好！")
    if err != nil {
        panic(err)
    }
    
    fmt.Println(response)
}
```

### 自定义工具

```go
agent := miniagent.NewAgent("your-api-key", "gpt-4o-mini")

// 注册自定义工具
agent.RegisterTool(
    "weather",
    func(ctx context.Context, args map[string]any) (string, error) {
        city := args["city"].(string)
        return fmt.Sprintf("%s 天气：晴，25°C", city), nil
    },
    "获取城市天气信息",
    map[string]miniagent.ParameterSchema{
        "city": {Type: "string", Description: "城市名称"},
    },
)
```

## CLI 用法

```bash
# 设置 API key
export OPENAI_API_KEY=your-api-key

# 单次查询
go run agent.go "1 + 1 等于多少？"

# 交互模式
go run agent.go
```

### 使用 Ollama（本地）

```bash
export OPENAI_API_KEY=ollama
go run agent.go
```

## 架构

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

## 内置工具

| 工具 | 描述 | 参数 |
|------|------|------|
| `shell` | 执行 Shell 命令 | `command: string` |
| `file_read` | 读取文件内容 | `path: string`, `max_lines?: number` |
| `file_write` | 写入文件 | `path: string`, `content: string` |
| `http_get` | HTTP GET 请求 | `url: string` |
| `http_post` | HTTP POST 请求 | `url: string`, `body?: string` |
| `calc` | 计算表达式 | `expression: string` |
| `time` | 获取当前时间 | `format?: string` |

## 嵌入示例

```go
// 创建可嵌入的 Agent
agent := miniagent.Embed("your-api-key", "gpt-4o-mini")

// 配置
agent.SetSystemPrompt("你是一个专业的编程助手。")
agent.RegisterTool("git_commit", gitCommitTool, "创建 Git 提交", nil)

// 使用
response, _ := agent.Run(ctx, "帮我提交代码，消息是 '修复bug'")
```

## 配置

```go
config := &miniagent.AgentConfig{
    SystemPrompt: "你是一个有用的助手。",
    MaxTokens:    4096,
    Temperature:   0.7,
    MaxIterations: 10,        // 最大工具调用迭代次数
    Tools:         miniagent.GetDefaultTools(),
}

agent := miniagent.NewAgentWithConfig("api-key", "gpt-4o-mini", config)
```

## 自定义 LLM Provider

```go
type MyProvider struct{}

func (p *MyProvider) Chat(ctx context.Context, messages []miniagent.Message) (*miniagent.ChatResponse, error) {
    // 你的实现
    return &miniagent.ChatResponse{
        Content: "来自自定义 Provider 的响应",
    }, nil
}

func (p *MyProvider) Name() string {
    return "my-provider"
}

agent := miniagent.NewAgentWithProvider(&MyProvider{})
```

## 对比

| 特性 | MiniAgent | LangChain | 其他框架 |
|------|-----------|-----------|----------|
| 代码行数 | ~1000 | 50000+ | 10000+ |
| 依赖数 | 0 | 50+ | 20+ |
| 可嵌入 | ✅ | ❌ | ⚠️ |
| Function Calling | ✅ | ✅ | ✅ |
| 学习曲线 | 低 | 高 | 中 |

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)。
