---
title: 磁盘与文件系统排查手册
fault_type: disk_and_filesystem
domains:
  - operating_system
  - container
  - database
  - logging
signals:
  - no space left on device
  - read-only file system
  - disk quota exceeded
  - too many open files
  - inode
  - 磁盘空间不足
severity_hint: critical
source_type: runbook
source_urls:
  - https://www.gnu.org/software/coreutils/manual/html_node/df-invocation.html
  - https://man7.org/linux/man-pages/man1/du.1.html
  - https://docs.docker.com/engine/logging/
---

# 磁盘与文件系统排查手册

## 适用场景

应用写日志、上传文件、数据库写入、容器运行或系统服务启动失败，日志提示磁盘空间不足、文件系统只读、inode 耗尽或文件句柄不足。

## 常见日志信号

- `No space left on device`
- `Read-only file system`
- `Disk quota exceeded`
- `Too many open files`
- `No such file or directory`
- `inode exhausted`
- `磁盘空间不足`

## 常见原因

- 日志文件增长过快，未配置轮转。
- 容器日志占满宿主机磁盘。
- 数据库数据文件或 binlog 占用过大。
- inode 耗尽，通常由大量小文件导致。
- 挂载目录错误或文件系统进入只读状态。
- 进程打开文件过多，超过系统限制。

## 排查步骤

查看磁盘和 inode：

```bash
df -h
df -i
du -sh *
```

查看大文件：

```bash
find /var/log -type f -size +100M
```

查看文件句柄：

```bash
ulimit -n
lsof -p <PID>
```

容器场景检查 Docker 日志目录、挂载卷和日志驱动配置。

## 修复建议

- 清理无用日志、临时文件和过期备份。
- 配置日志轮转和保留周期。
- 扩容磁盘或迁移数据目录。
- 修正挂载路径和目录权限。
- 调整文件句柄限制并排查句柄泄漏。

## 预防建议

- 对磁盘使用率、inode、日志增长量设置告警。
- 容器日志配置大小限制和轮转。
- 数据库备份、binlog 和归档文件设置生命周期。
- 生产环境清理文件前确认业务影响，避免误删关键数据。

## 参考来源

- GNU `df` 文档
- Linux `du` 文档
- Docker logging 文档
