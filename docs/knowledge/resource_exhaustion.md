---
title: 资源耗尽排查手册
fault_type: resource_exhaustion
domains:
  - application
  - operating_system
  - container
  - database
  - cloud_service
signals:
  - out of memory
  - too many open files
  - connection pool exhausted
  - cpu throttling
  - no buffer space available
  - 资源耗尽
severity_hint: critical
source_type: runbook
source_urls:
  - https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
  - https://docs.docker.com/engine/containers/resource_constraints/
  - https://docs.oracle.com/javase/8/docs/technotes/guides/troubleshoot/memleaks.html
---

# 资源耗尽排查手册

## 适用场景

应用或基础设施因 CPU、内存、磁盘、文件句柄、线程池、连接池或容器资源限制耗尽而出现性能下降、请求失败、进程退出或服务不可用。

## 常见日志信号

- `OutOfMemoryError`
- `OOMKilled`
- `Too many open files`
- `Connection pool exhausted`
- `Timeout waiting for connection`
- `CPU throttling`
- `No buffer space available`

## 常见原因

- 内存泄漏或瞬时大对象分配。
- 容器 memory limit 过低。
- 数据库、HTTP 或 Redis 连接池耗尽。
- 线程池队列积压或死锁。
- 文件句柄未释放。
- 磁盘空间或 inode 耗尽。
- 流量突增导致资源超出容量。

## 排查步骤

查看系统资源：

```bash
top
free -m
df -h
ulimit -n
```

容器/Kubernetes：

```bash
docker stats
kubectl top pod
kubectl describe pod <pod>
```

Java 应用可检查 heap、GC、线程栈和连接池指标。数据库场景应查看连接数、锁等待和慢查询。

## 修复建议

- 临时扩容实例、容器资源或连接池上限。
- 修复连接、文件句柄、线程等资源泄漏。
- 优化慢查询和高内存操作。
- 对高峰流量增加限流、队列、缓存或降级。
- 对 JVM OOM 保留 heap dump 并分析对象占用。

## 预防建议

- 为 CPU、内存、连接池、线程池、磁盘设置监控告警。
- 容器设置合理 requests/limits。
- 压测验证容量边界。
- 对资源耗尽类故障保留现场数据，避免直接重启后失去证据。

## 参考来源

- Kubernetes container resources 文档
- Docker resource constraints 文档
- Oracle JVM memory troubleshooting 文档
