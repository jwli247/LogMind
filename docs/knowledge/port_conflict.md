---
title: 端口冲突排查手册
fault_type: port_conflict
domains:
  - application
  - container
  - operating_system
  - gateway
signals:
  - address already in use
  - port already in use
  - port is already allocated
  - EADDRINUSE
  - 端口被占用
severity_hint: medium
source_type: runbook
source_urls:
  - https://docs.spring.io/spring-boot/reference/features/spring-application.html
  - https://docs.docker.com/reference/cli/docker/container/run/
  - https://nodejs.org/api/errors.html
---

# 端口冲突排查手册

## 适用场景

应用服务、网关、容器或本地开发进程启动失败，日志提示端口已被占用。常见于 Web 服务启动、Docker 端口映射、Nginx/Tomcat 监听端口、本地重复启动服务等场景。

## 常见日志信号

- `Port 8080 was already in use`
- `Address already in use`
- `EADDRINUSE`
- `BindException`
- `port is already allocated`
- `listen tcp 0.0.0.0:8080: bind: address already in use`

## 常见原因

- 旧进程未退出，仍占用原端口。
- 本地重复启动同一个应用。
- Docker 容器端口映射与宿主机已有进程冲突。
- 网关、Tomcat、Nginx 或其他服务监听了相同端口。
- 服务配置在不同环境中复用了相同端口。

## 排查步骤

Windows：

```powershell
netstat -ano | findstr ":8080"
tasklist | findstr <PID>
```

Linux/macOS：

```bash
lsof -i :8080
ss -lntp | grep 8080
```

Docker 场景：

```bash
docker ps
docker port <container>
```

如果是应用配置问题，检查 `server.port`、启动参数、容器端口映射和网关监听端口是否冲突。

## 修复建议

- 如果占用端口的是旧实例，可以停止旧进程。
- 如果端口被其他服务正常使用，修改当前服务端口。
- Docker 中可调整宿主机端口映射，例如 `-p 8081:8080`。
- 本地开发环境建议为每个服务规划固定端口。

## 预防建议

- 启动脚本中增加端口占用检查。
- 开发环境维护端口分配表。
- 容器编排中统一管理端口映射。
- 生产环境停止进程前应确认流量、依赖和回滚方案。

## 参考来源

- Spring Boot Startup Failure 文档
- Docker `run` 端口映射文档
- Node.js `EADDRINUSE` 错误说明
