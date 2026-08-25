---
title: 网关 5xx 错误排查手册
fault_type: gateway_5xx
domains:
  - gateway
  - application
  - load_balancer
  - cloud_service
signals:
  - 502 bad gateway
  - 503 service unavailable
  - 504 gateway timeout
  - upstream timed out
  - connect() failed
severity_hint: high
source_type: runbook
source_urls:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504
---

# 网关 5xx 错误排查手册

## 适用场景

用户通过 Nginx、API Gateway、负载均衡或反向代理访问服务时出现 502、503、504 等 5xx 错误。该类问题通常表示网关无法从上游服务获得正常响应。

## 常见日志信号

- `502 Bad Gateway`
- `503 Service Unavailable`
- `504 Gateway Timeout`
- `upstream timed out`
- `connect() failed while connecting to upstream`
- `connection refused while connecting to upstream`

## 常见原因

- 后端服务未启动、崩溃或健康检查失败。
- upstream 地址、端口或协议配置错误。
- 后端服务响应过慢，超过网关 timeout。
- 后端连接数、线程池或数据库连接池耗尽。
- 负载均衡目标组无健康实例。
- 网络、安全组或容器网络配置异常。

## 排查步骤

检查网关错误日志：

```bash
tail -f /var/log/nginx/error.log
```

检查 upstream 配置：

```nginx
upstream backend {
    server 127.0.0.1:8080;
}
```

检查后端健康状态：

```bash
curl -v http://127.0.0.1:8080/health
```

云负载均衡场景需查看目标组健康检查、监听器规则、安全组和实例状态。

## 修复建议

- 恢复或重启异常后端服务。
- 修正 upstream 地址、端口、协议和健康检查路径。
- 对后端慢响应问题排查数据库、缓存、线程池和外部依赖。
- 合理设置 `proxy_connect_timeout`、`proxy_read_timeout`、重试和熔断策略。

## 预防建议

- 所有服务提供健康检查接口。
- 监控网关 5xx 错误率和 upstream 响应时间。
- 发布前验证 upstream、端口、健康检查和回滚策略。
- 关键服务配置限流、熔断和降级能力。

## 参考来源

- Nginx proxy module 文档
- MDN HTTP 502/503/504 状态码文档
