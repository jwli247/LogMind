---
title: Kubernetes Pod 异常排查手册
fault_type: kubernetes_pod_failure
domains:
  - kubernetes
  - container
  - cloud_service
signals:
  - crashloopbackoff
  - imagepullbackoff
  - oomkilled
  - readiness probe failed
  - liveness probe failed
  - pod pending
severity_hint: high
source_type: runbook
source_urls:
  - https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
  - https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
  - https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
---

# Kubernetes Pod 异常排查手册

## 适用场景

Kubernetes Pod 无法启动、反复重启、镜像拉取失败、健康检查失败、资源不足或一直处于 Pending。该类问题需要同时查看 Pod 状态、事件、容器日志和资源配置。

## 常见日志信号

- `CrashLoopBackOff`
- `ImagePullBackOff`
- `ErrImagePull`
- `OOMKilled`
- `Readiness probe failed`
- `Liveness probe failed`
- `Pending`

## 常见原因

- 应用进程启动失败或启动后立即退出。
- 镜像名、tag 或镜像仓库凭证错误。
- 内存限制过低导致 OOMKilled。
- readiness/liveness probe 配置错误。
- 节点资源不足或调度约束不满足。
- ConfigMap、Secret、PVC 或 ServiceAccount 配置错误。

## 排查步骤

查看 Pod 状态和事件：

```bash
kubectl describe pod <pod>
kubectl get events --sort-by=.lastTimestamp
```

查看日志：

```bash
kubectl logs <pod>
kubectl logs <pod> --previous
```

查看资源和探针：

```bash
kubectl get pod <pod> -o yaml
kubectl top pod
```

## 修复建议

- 根据容器日志修复应用启动错误。
- 修正镜像地址、tag 和 imagePullSecret。
- 调整 requests/limits，避免资源过低。
- 修正健康检查路径、端口、初始延迟和超时时间。
- 检查 ConfigMap、Secret、PVC 和节点调度条件。

## 预防建议

- 发布前验证镜像可拉取、配置可加载、探针可通过。
- 为 Pod 设置合理资源请求和限制。
- 监控重启次数、Pod 状态和 OOMKilled。
- 保留上一轮容器日志，便于 CrashLoopBackOff 排查。

## 参考来源

- Kubernetes Debug Pods 文档
- Kubernetes Pod lifecycle 文档
- Kubernetes probes 文档
