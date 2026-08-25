---
title: TLS、DNS 与网络排查手册
fault_type: tls_dns_network
domains:
  - network
  - cloud_service
  - gateway
  - security
signals:
  - ssl handshake failed
  - certificate expired
  - name resolution failed
  - no route to host
  - connection reset
  - dns lookup failed
severity_hint: high
source_type: runbook
source_urls:
  - https://developer.mozilla.org/en-US/docs/Web/Security/Transport_Layer_Security
  - https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
  - https://www.openssl.org/docs/manmaster/man1/openssl-s_client.html
---

# TLS、DNS 与网络排查手册

## 适用场景

服务间调用、外部 API 访问、域名访问或 HTTPS 请求失败，日志指向 DNS 解析、TLS 证书、网络路由、连接重置或安全策略问题。

## 常见日志信号

- `SSL handshake failed`
- `certificate has expired`
- `unable to verify the first certificate`
- `Name resolution failed`
- `DNS lookup failed`
- `No route to host`
- `Connection reset by peer`

## 常见原因

- 域名解析错误、DNS 缓存异常或 CoreDNS 问题。
- 证书过期、证书链不完整或域名不匹配。
- 客户端和服务端 TLS 协议或 cipher 不兼容。
- 防火墙、安全组、网络 ACL 或代理阻断。
- 服务端关闭连接或负载均衡后端异常。
- Kubernetes 集群内 DNS 或 Service 配置错误。

## 排查步骤

检查 DNS：

```bash
nslookup <domain>
dig <domain>
```

检查网络连通性：

```bash
curl -v https://<domain>
nc -vz <host> <port>
```

检查证书：

```bash
openssl s_client -connect <domain>:443 -servername <domain>
```

Kubernetes 场景可检查 CoreDNS、Service、Endpoints 和 NetworkPolicy。

## 修复建议

- 修正 DNS 记录、Service 或负载均衡配置。
- 更新过期证书并补齐证书链。
- 调整 TLS 协议和 cipher 配置。
- 修正安全组、防火墙、代理和网络策略。
- 对连接重置问题检查服务端日志和负载均衡健康状态。

## 预防建议

- 为证书过期设置提前告警。
- 对 DNS 解析失败率和网络错误率设置监控。
- 发布前验证域名、证书、Service 和安全组。
- 日志中避免输出敏感请求头、Token 和证书私钥。

## 参考来源

- MDN TLS 文档
- Kubernetes DNS debugging 文档
- OpenSSL `s_client` 文档
