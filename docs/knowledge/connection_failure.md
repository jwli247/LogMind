---
title: 连接失败排查手册
fault_type: connection_failure
domains:
  - application
  - database
  - cache
  - message_queue
  - cloud_service
  - network
signals:
  - connection refused
  - connection reset
  - no route to host
  - communications link failure
  - access denied
  - 连接失败
severity_hint: high
source_type: runbook
source_urls:
  - https://redis.io/docs/latest/develop/reference/clients/
  - https://dev.mysql.com/doc/refman/8.4/en/problems-connecting.html
  - https://www.postgresql.org/docs/current/client-authentication.html
---

# 连接失败排查手册

## 适用场景

应用连接数据库、缓存、消息队列、HTTP 服务或云服务失败。该类问题常见于服务未启动、地址端口错误、网络不通、安全组限制、账号权限错误和连接池配置问题。

## 常见日志信号

- `Connection refused`
- `Connection reset by peer`
- `No route to host`
- `Communications link failure`
- `Access denied for user`
- `Could not connect to server`
- `Name or service not known`
- `连接失败`、`无法连接`、`拒绝连接`

## 常见原因

- 目标服务未启动或监听端口错误。
- 应用配置中的 host、port、database、username、password 错误。
- 防火墙、安全组、网络策略或 Kubernetes NetworkPolicy 阻断。
- DNS 解析异常，域名指向错误地址。
- 数据库、缓存或 MQ 达到最大连接数。
- 账号认证失败或权限不足。

## 排查步骤

确认目标地址和端口：

```bash
nc -vz <host> <port>
telnet <host> <port>
```

数据库连接可用性：

```bash
mysql -h <host> -P <port> -u <user> -p
psql -h <host> -p <port> -U <user>
```

Redis：

```bash
redis-cli -h <host> -p <port> ping
```

云服务场景应检查 VPC、安全组、白名单、专有网络和访问凭证。

## 修复建议

- 修正连接串、账号、密码、端口和数据库名称。
- 启动目标服务或恢复异常实例。
- 调整防火墙、安全组或网络策略。
- 增大连接池或释放泄漏连接。
- 对云服务确认区域、网络类型和白名单配置。

## 预防建议

- 为关键依赖增加健康检查。
- 监控连接数、错误率和连接池等待时间。
- 配置变更前在测试环境验证连接。
- 日志中避免输出明文密码、Token 和完整连接串。

## 参考来源

- Redis client handling 文档
- MySQL connection troubleshooting 文档
- PostgreSQL client authentication 文档
