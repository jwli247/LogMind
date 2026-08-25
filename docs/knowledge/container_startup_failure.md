---
title: 容器启动失败排查手册
fault_type: container_startup_failure
domains:
  - container
  - application
  - deployment
signals:
  - container exited
  - exited with code
  - image pull failed
  - unhealthy
  - port is already allocated
  - 容器启动失败
severity_hint: high
source_type: runbook
source_urls:
  - https://docs.docker.com/reference/cli/docker/container/logs/
  - https://docs.docker.com/reference/cli/docker/container/inspect/
  - https://docs.docker.com/engine/containers/start-containers-automatically/
---

# 容器启动失败排查手册

## 适用场景

Docker 容器启动后立即退出、无法拉取镜像、健康检查失败、端口映射冲突或环境变量缺失。该类问题可能来自应用本身，也可能来自镜像、运行参数或宿主机环境。

## 常见日志信号

- `container exited with code 1`
- `Error response from daemon`
- `port is already allocated`
- `No such file or directory`
- `exec format error`
- `unhealthy`
- `image pull failed`

## 常见原因

- 应用启动命令或 entrypoint 错误。
- 必需环境变量未传入。
- 镜像架构与宿主机不匹配。
- 端口映射冲突。
- 挂载文件或目录不存在。
- 容器资源限制过低。
- 健康检查命令错误或服务启动较慢。

## 排查步骤

查看容器状态和日志：

```bash
docker ps -a
docker logs <container>
docker inspect <container>
```

检查启动命令、环境变量、挂载路径、端口映射和健康检查配置。若是镜像拉取失败，检查镜像名、tag、仓库权限和网络。

## 修复建议

- 修正 entrypoint、command 和启动参数。
- 补齐环境变量和 Secret。
- 修正端口映射和卷挂载路径。
- 调整健康检查延迟和重试次数。
- 选择正确平台架构的镜像。

## 预防建议

- 镜像构建后在本地或测试环境启动验证。
- 使用 Compose 或部署模板统一管理运行参数。
- 健康检查应考虑应用冷启动时间。
- 容器日志中避免输出敏感环境变量。

## 参考来源

- Docker logs 文档
- Docker inspect 文档
- Docker restart policy 文档
