# 安全合规

## 威胁模型

| 威胁 | 缓解措施 |
|---|---|
| 未授权访问 API | JWT + RBAC（admin/user） |
| 暴力破解 | 速率限制（slowapi，120 req/min） |
| 密钥泄露 | 环境变量 + .gitignore 排除 .env |
| 数据篡改 | JWT 签名校验 + 来源 source_ids 多源校验 |
| Prompt 注入 | LLM 解析器使用 JSON mode + 严格字段校验 |
| 爬取法律风险 | robots.txt 校验 + 限流 + 法律声明 |

## 数据保护

- 敏感字段不写入日志（headers 中的 Authorization 自动过滤）
- PII 字段（如有）在 v2 加入 pydantic 脱敏注解
- 数据库密码通过环境变量注入

## 合规

- 抓取行为遵守 `robots.txt`（v2 计划集成 robotexclusionrulesparser）
- 限流：默认 60 req/min，可按源配置
- 法律声明：`config/legal_notice.md`
