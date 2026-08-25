---
title: 权限与认证失败排查手册
fault_type: permission_and_auth
domains:
  - application
  - database
  - operating_system
  - cloud_service
  - security
signals:
  - permission denied
  - access denied
  - unauthorized
  - forbidden
  - invalid token
  - 认证失败
severity_hint: high
source_type: runbook
source_urls:
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
  - https://www.postgresql.org/docs/current/client-authentication.html
  - https://dev.mysql.com/doc/refman/8.4/en/access-denied.html
---

# 权限与认证失败排查手册

## 适用场景

应用访问文件、接口、数据库、对象存储、云服务或系统资源时被拒绝。该类问题既可能是认证失败，也可能是权限不足、凭证过期或策略配置错误。

## 常见日志信号

- `401 Unauthorized`
- `403 Forbidden`
- `Permission denied`
- `Access denied`
- `Invalid token`
- `Signature expired`
- `Access denied for user`
- `拒绝访问`、`权限不足`

## 常见原因

- 用户名、密码、Token、AK/SK 或证书错误。
- Token 过期、签名时间偏差或权限范围不足。
- 文件或目录权限不允许当前进程访问。
- 数据库账号缺少目标库表权限。
- 云服务 IAM 策略、Bucket Policy 或安全组配置不正确。
- 环境变量未正确注入，导致使用了空凭证或旧凭证。

## 排查步骤

先确认失败对象：

- HTTP 接口
- 数据库
- 文件系统
- 云服务
- 容器挂载卷

检查当前运行用户和权限：

```bash
whoami
ls -l <path>
```

数据库场景检查账号、host、权限和认证方式。HTTP 场景检查请求头、Token 有效期、权限范围和服务端鉴权日志。

## 修复建议

- 更新或重新生成有效凭证。
- 修正数据库账号权限和访问来源。
- 调整文件、目录或挂载卷权限。
- 修正 IAM/ACL/Policy 配置。
- 确保环境变量、Secret 和配置中心中的凭证正确。

## 预防建议

- 凭证使用 Secret 管理，不写入代码和日志。
- 为 Token 和证书设置过期监控。
- 最小权限原则授权。
- 排障输出中必须脱敏账号、Token、密码和签名参数。

## 参考来源

- MDN HTTP 401/403 文档
- PostgreSQL client authentication 文档
- MySQL access denied 文档
