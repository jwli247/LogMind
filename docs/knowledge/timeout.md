---
title: 超时问题排查手册
fault_type: timeout
domains:
  - application
  - database
  - cache
  - gateway
  - network
  - cloud_service
signals:
  - timeout
  - timed out
  - read timed out
  - gateway timeout
  - deadline exceeded
  - 超时
severity_hint: high
source_type: runbook
source_urls:
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  - https://redis.io/docs/latest/operate/rs/databases/connect/troubleshooting-guide/
---

# 超时问题排查手册

## 适用场景

请求、数据库查询、缓存访问、网关转发、第三方 API 调用或云服务访问超过预期时间。超时通常不是单点问题，可能来自网络、依赖服务、资源瓶颈或配置过短。

## 常见日志信号

- `Read timed out`
- `Connection timed out`
- `Gateway Timeout`
- `upstream timed out`
- `context deadline exceeded`
- `Timeout waiting for connection from pool`
- `请求超时`、`连接超时`

## 常见原因

- 下游服务响应慢或不可用。
- 数据库慢查询、锁等待或连接池耗尽。
- Redis、MQ 或第三方 API 延迟升高。
- Nginx、网关或客户端 timeout 配置过短。
- 网络抖动、跨地域访问或 DNS 异常。
- CPU、线程池、连接池、磁盘 I/O 等资源瓶颈。

## 排查步骤

先确认超时发生在哪一层：

- 客户端超时
- 网关超时
- 应用内部调用超时
- 数据库或缓存超时
- 第三方 API 超时

检查日志中的耗时字段、trace_id、span、上游地址和下游接口。对数据库慢查询，查看慢 SQL 日志和执行计划。对网关超时，查看 Nginx 或 API Gateway 错误日志。

## 修复建议

- 优先定位真实慢点，不要只盲目调大 timeout。
- 对慢 SQL 增加索引或优化查询。
- 对高延迟接口增加缓存、降级或异步处理。
- 合理配置客户端、网关和服务端 timeout。
- 对连接池耗尽问题，检查连接泄漏和池大小。

## 预防建议

- 建立端到端链路追踪和耗时监控。
- 为关键依赖配置超时、重试、熔断和降级。
- 对慢查询、P95/P99 延迟和错误率设置告警。
- 生产环境调整 timeout 前应评估重试风暴和资源占用。

## 参考来源

- MDN HTTP 504 文档
- Nginx proxy timeout 文档
- Redis connection troubleshooting 文档
