---
title: 数据库慢查询排查手册
fault_type: database_slow_query
domains:
  - database
  - application
  - performance
signals:
  - slow query
  - lock wait timeout
  - query timeout
  - full table scan
  - deadlock
  - 慢查询
severity_hint: high
source_type: runbook
source_urls:
  - https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html
  - https://dev.mysql.com/doc/refman/8.4/en/using-explain.html
  - https://www.postgresql.org/docs/current/using-explain.html
---

# 数据库慢查询排查手册

## 适用场景

接口响应慢、数据库 CPU 升高、连接池等待、查询超时或事务阻塞。该类问题常见于慢 SQL、索引缺失、锁等待、事务过长和数据量增长。

## 常见日志信号

- `slow query`
- `Query timeout`
- `Lock wait timeout exceeded`
- `Deadlock found`
- `Timeout waiting for connection from pool`
- `Using filesort`
- `Full table scan`

## 常见原因

- 查询条件缺少索引或索引失效。
- 返回数据量过大，分页不合理。
- 事务持有锁时间过长。
- 表统计信息过期或执行计划不佳。
- 连接池耗尽，应用请求等待连接。
- 数据库实例 CPU、I/O 或内存达到瓶颈。

## 排查步骤

查看慢查询日志和执行计划：

```sql
EXPLAIN SELECT ...;
```

MySQL 可查看慢查询日志、锁等待和连接数。PostgreSQL 可使用 `EXPLAIN ANALYZE`、`pg_stat_activity` 和慢查询日志。应用侧需要检查连接池等待时间、SQL 参数和调用链耗时。

## 修复建议

- 为高频过滤、排序和关联字段建立合适索引。
- 避免无条件全表扫描和大分页。
- 缩短事务范围，减少锁持有时间。
- 优化 SQL、拆分复杂查询或增加缓存。
- 调整连接池大小前先确认数据库容量。

## 预防建议

- 开启慢查询监控和 SQL 审计。
- 重要 SQL 上线前查看执行计划。
- 对表数据量增长设置容量预警。
- 监控连接池等待、数据库 CPU、I/O、锁等待和慢 SQL 数量。

## 参考来源

- MySQL slow query log 文档
- MySQL EXPLAIN 文档
- PostgreSQL EXPLAIN 文档
