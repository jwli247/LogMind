---
title: 配置错误排查手册
fault_type: configuration_error
domains:
  - application
  - container
  - cloud_service
  - deployment
signals:
  - could not resolve placeholder
  - failed to bind properties
  - invalid configuration
  - missing environment variable
  - yaml parse
  - 配置错误
severity_hint: medium
source_type: runbook
source_urls:
  - https://docs.spring.io/spring-boot/reference/features/external-config.html
  - https://docs.docker.com/compose/environment-variables/
  - https://kubernetes.io/docs/concepts/configuration/configmap/
---

# 配置错误排查手册

## 适用场景

应用启动失败、连接目标错误、环境不一致或行为异常，日志指向配置缺失、格式错误、类型转换失败或环境变量未注入。

## 常见日志信号

- `Could not resolve placeholder`
- `Failed to bind properties`
- `Invalid configuration`
- `Missing required environment variable`
- `YAML parse error`
- `No such file or directory`
- `配置错误`、`配置文件解析失败`

## 常见原因

- 环境变量未设置或变量名拼写错误。
- YAML/JSON/properties 格式错误。
- 配置值类型不匹配，例如字符串绑定到整数。
- 不同环境使用了错误 profile。
- 容器或 Kubernetes ConfigMap/Secret 未正确挂载。
- 配置中心发布了错误版本。

## 排查步骤

确认实际加载的环境和 profile：

```bash
printenv
```

检查配置文件格式、缩进和变量名。容器场景检查启动命令、环境变量、挂载路径和 ConfigMap/Secret。云服务场景检查配置中心版本和灰度范围。

## 修复建议

- 补齐缺失环境变量或配置项。
- 修复 YAML 缩进、JSON 格式和类型错误。
- 确认当前环境 profile 正确。
- 回滚错误配置版本。
- 对敏感配置使用 Secret，不放入普通配置文件。

## 预防建议

- 为关键配置增加启动时校验。
- 配置变更走审查、灰度和回滚流程。
- 建立配置模板和环境差异说明。
- 在日志中避免输出密码、Token 和密钥。

## 参考来源

- Spring Boot Externalized Configuration 文档
- Docker Compose environment variables 文档
- Kubernetes ConfigMap 文档
