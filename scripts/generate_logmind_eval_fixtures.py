import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def _eval_case(
    case_id: str,
    name: str,
    dataset: str,
    source_url: str,
    note: str,
    text: str,
    fault_type: str,
    evidence: list[str],
) -> dict:
    return {
        "id": case_id,
        "name": name,
        "dataset": dataset,
        "source_url": source_url,
        "annotation_note": note,
        "input_text": text,
        "expected_fault_type": fault_type,
        "expected_diagnostic_request": True,
        "required_input_evidence": evidence,
    }


def build_public_log_cases() -> list[dict]:
    rows = [
        ("apache_permission_denied", "Apache 权限拒绝", "LogHub Apache", "Apache", "Permission denied: access to /admin denied", "permission_and_auth", ["Permission denied"]),
        ("apache_file_missing", "Apache 文件缺失", "LogHub Apache", "Apache", "File does not exist: /var/www/html/favicon.ico", "unknown", ["File does not exist"]),
        ("apache_client_denied", "Apache 客户端访问拒绝", "LogHub Apache", "Apache", "client denied by server configuration: /srv/www/private", "permission_and_auth", ["denied"]),
        ("apache_invalid_method", "Apache 非法请求", "LogHub Apache", "Apache", "Invalid method in request BAD / HTTP/1.1", "unknown", ["Invalid method"]),
        ("openssh_failed_password", "OpenSSH 登录失败", "LogHub OpenSSH", "OpenSSH", "Failed password for invalid user admin from 10.0.0.8 port 55231 ssh2", "permission_and_auth", ["Failed password"]),
        ("openssh_connection_closed", "OpenSSH 连接关闭", "LogHub OpenSSH", "OpenSSH", "Connection closed by authenticating user app 10.0.0.8 port 55231", "connection_failure", ["Connection closed"]),
        ("openssh_auth_failure", "OpenSSH 认证失败", "LogHub OpenSSH", "OpenSSH", "Authentication failure for illegal user test from 10.0.0.9", "permission_and_auth", ["Authentication failure"]),
        ("openssh_refused_connect", "OpenSSH 连接拒绝", "LogHub OpenSSH", "OpenSSH", "connect to 10.0.0.10 port 22: Connection refused", "connection_failure", ["Connection refused"]),
        ("hdfs_connection_refused", "HDFS 连接拒绝", "LogHub HDFS", "HDFS", "Retrying connect to server datanode:50010 because connection refused", "connection_failure", ["connection refused"]),
        ("hdfs_io_exception", "HDFS IO 异常", "LogHub HDFS", "HDFS", "DataStreamer Exception java.io.IOException: Broken pipe", "unknown", ["IOException"]),
        ("hdfs_timeout", "HDFS 超时", "LogHub HDFS", "HDFS", "Call to namenode timed out after 60000ms", "timeout", ["timed out"]),
        ("hdfs_disk_full", "HDFS 磁盘空间", "LogHub HDFS", "HDFS", "IOException while writing block: No space left on device", "disk_and_filesystem", ["No space left on device"]),
        ("openstack_connection_refused", "OpenStack 连接拒绝", "LogHub OpenStack", "OpenStack", "Connection refused while connecting to libvirt service", "connection_failure", ["Connection refused"]),
        ("openstack_instance_failed", "OpenStack 实例启动失败", "LogHub OpenStack", "OpenStack", "Instance failed to spawn: container exited unexpectedly", "container_startup_failure", ["container exited"]),
        ("openstack_unauthorized", "OpenStack 未授权", "LogHub OpenStack", "OpenStack", "Unauthorized: the request requires authentication", "permission_and_auth", ["Unauthorized"]),
        ("openstack_timeout", "OpenStack 服务超时", "LogHub OpenStack", "OpenStack", "Timeout while waiting on RPC response from compute service", "timeout", ["Timeout"]),
        ("zookeeper_session_timeout", "ZooKeeper 会话超时", "LogHub ZooKeeper", "Zookeeper", "Client session timed out, have not heard from server in 30000ms", "timeout", ["session timed out"]),
        ("zookeeper_connection_loss", "ZooKeeper 连接丢失", "LogHub ZooKeeper", "Zookeeper", "Connection refused to server zookeeper:2181", "connection_failure", ["Connection refused"]),
        ("zookeeper_auth_failed", "ZooKeeper 认证失败", "LogHub ZooKeeper", "Zookeeper", "Authentication failed for session", "permission_and_auth", ["Authentication failed"]),
        ("zookeeper_unknown_exception", "ZooKeeper 通用异常", "LogHub ZooKeeper", "Zookeeper", "Unexpected exception while processing request", "unknown", ["Unexpected exception"]),
        ("bgl_io_error", "BGL 系统 IO 错误", "LogHub BGL", "BGL", "I/O error detected on device during filesystem operation", "unknown", ["I/O error"]),
        ("bgl_memory_oom", "BGL 内存不足", "LogHub BGL", "BGL", "Out of memory: Kill process 23891 java score 987", "resource_exhaustion", ["Out of memory"]),
        ("bgl_filesystem_readonly", "BGL 文件系统只读", "LogHub BGL", "BGL", "Remounting filesystem read-only after journal failure", "disk_and_filesystem", ["read-only"]),
        ("bgl_connection_timeout", "BGL 网络超时", "LogHub BGL", "BGL", "connection timed out while sending heartbeat to management node", "timeout", ["connection timed out"]),
        ("hadoop_bind_error", "Hadoop 端口绑定", "LogHub Hadoop", "Hadoop", "java.net.BindException: Address already in use", "port_conflict", ["Address already in use"]),
        ("hadoop_config_missing", "Hadoop 配置缺失", "LogHub Hadoop", "Hadoop", "Could not resolve placeholder HADOOP_HOME", "configuration_error", ["Could not resolve placeholder"]),
        ("hadoop_permission_denied", "Hadoop 权限拒绝", "LogHub Hadoop", "Hadoop", "Permission denied: user app cannot write /warehouse", "permission_and_auth", ["Permission denied"]),
        ("hadoop_slow_query_boundary", "Hadoop 慢任务", "LogHub Hadoop", "Hadoop", "slow query stage took 18.5s and rows_examined=1200000", "database_slow_query", ["slow query"]),
        ("spark_executor_lost", "Spark Executor 退出", "LogHub Spark", "Spark", "Lost executor because container exited with code 137", "container_startup_failure", ["container exited"]),
        ("spark_oom", "Spark OOM", "LogHub Spark", "Spark", "java.lang.OutOfMemoryError: Java heap space while running task", "resource_exhaustion", ["OutOfMemoryError"]),
        ("spark_fetch_timeout", "Spark 拉取超时", "LogHub Spark", "Spark", "request timeout while fetching shuffle blocks", "timeout", ["request timeout"]),
        ("spark_connection_refused", "Spark 连接拒绝", "LogHub Spark", "Spark", "Connection refused when connecting to executor backend", "connection_failure", ["Connection refused"]),
        ("linux_disk_full", "Linux 磁盘满", "LogHub Linux", "Linux", "No space left on device while writing journal", "disk_and_filesystem", ["No space left on device"]),
        ("linux_tls_handshake", "Linux TLS 握手失败", "LogHub Linux", "Linux", "tls handshake failed: certificate verify failed", "tls_dns_network", ["tls handshake"]),
        ("linux_dns_unknown_host", "Linux DNS 解析失败", "LogHub Linux", "Linux", "dns lookup failed for api.internal: name or service not known", "tls_dns_network", ["dns lookup failed"]),
        ("linux_too_many_files", "Linux 文件句柄耗尽", "LogHub Linux", "Linux", "too many open files while accepting new connection", "resource_exhaustion", ["too many open files"]),
        ("thunderbird_timeout", "Thunderbird 超时", "LogHub Thunderbird", "Thunderbird", "read timed out while checking backend health", "timeout", ["read timed out"]),
        ("thunderbird_gateway", "Thunderbird 网关错误", "LogHub Thunderbird", "Thunderbird", "502 bad gateway from upstream service", "gateway_5xx", ["502 bad gateway"]),
        ("thunderbird_config_error", "Thunderbird 配置错误", "LogHub Thunderbird", "Thunderbird", "failed to bind properties under service.mail", "configuration_error", ["failed to bind properties"]),
        ("thunderbird_unknown_error", "Thunderbird 通用错误", "LogHub Thunderbird", "Thunderbird", "unexpected error while rotating background worker", "unknown", ["unexpected error"]),
    ]
    return [
        _eval_case(
            f"public_{case_id}",
            f"{name}公开日志样本",
            dataset,
            f"https://github.com/logpai/loghub/tree/master/{folder}",
            f"基于 {dataset} 公开日志风格脱敏标注。",
            f"ERROR {text}",
            fault_type,
            evidence,
        )
        for case_id, name, dataset, folder, text, fault_type, evidence in rows
    ]


def build_external_cases() -> list[dict]:
    rows = [
        ("spring_boot_port_conflict", "Spring Boot 端口占用", "https://docs.spring.io/spring-boot/reference/web/web-server.html", "APPLICATION FAILED TO START. Web server failed to start. Port 8080 was already in use.", "port_conflict", ["Port 8080"]),
        ("spring_boot_config_placeholder", "Spring Boot 配置占位符缺失", "https://docs.spring.io/spring-boot/reference/features/external-config.html", "Could not resolve placeholder DB_HOST. Application failed to start.", "configuration_error", ["Could not resolve placeholder"]),
        ("spring_boot_bind_properties", "Spring Boot 配置绑定失败", "https://docs.spring.io/spring-boot/reference/features/external-config.html", "Failed to bind properties under spring.datasource.url. Configuration property is invalid.", "configuration_error", ["Failed to bind properties"]),
        ("spring_boot_null_pointer", "Spring Boot 空指针异常", "https://docs.oracle.com/javase/8/docs/api/java/lang/NullPointerException.html", "java.lang.NullPointerException: Cannot invoke service because repository is null", "configuration_error", ["NullPointerException"]),
        ("mysql_access_denied", "MySQL 认证失败", "https://dev.mysql.com/doc/refman/8.4/en/problems-connecting.html", "java.sql.SQLException: Access denied for user app_user while connecting to MySQL.", "connection_failure", ["Access denied for user"]),
        ("mysql_communications_link", "MySQL 链路失败", "https://dev.mysql.com/doc/refman/8.4/en/problems-connecting.html", "Communications link failure to database.", "connection_failure", ["Communications link failure"]),
        ("mysql_slow_query", "MySQL 慢查询", "https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html", "Slow query detected: SELECT * FROM orders took 18.5s rows_examined=1200000.", "database_slow_query", ["Slow query"]),
        ("mysql_sql_syntax_error", "SQL 语法错误", "https://dev.mysql.com/doc/refman/8.4/en/problems-with-mysql.html", "java.sql.SQLSyntaxErrorException: You have an error in your SQL syntax near from order.", "database_slow_query", ["SQLSyntaxErrorException"]),
        ("nginx_502", "Nginx 502", "https://nginx.org/en/docs/http/ngx_http_proxy_module.html", "Nginx 502 Bad Gateway: upstream prematurely closed connection while reading response header from upstream.", "gateway_5xx", ["502 Bad Gateway"]),
        ("nginx_504_timeout", "Nginx 504 超时", "https://nginx.org/en/docs/http/ngx_http_proxy_module.html", "Nginx error: upstream timed out while reading response header, returned 504 gateway timeout.", "gateway_5xx", ["upstream timed out"]),
        ("nginx_connect_failed", "Nginx upstream 连接失败", "https://nginx.org/en/docs/http/ngx_http_proxy_module.html", "Nginx connect() failed while connecting to upstream, returned 502 bad gateway.", "gateway_5xx", ["connect() failed"]),
        ("nginx_port_bind", "Nginx 端口绑定失败", "https://nginx.org/en/docs/beginners_guide.html", "nginx bind failed: Address already in use.", "port_conflict", ["Address already in use"]),
        ("java_oom_heap", "Java 堆内存溢出", "https://docs.oracle.com/javase/8/docs/technotes/guides/troubleshoot/memleaks002.html", "Exception in thread main java.lang.OutOfMemoryError: Java heap space", "resource_exhaustion", ["OutOfMemoryError"]),
        ("java_gc_overhead", "Java GC 开销超限", "https://docs.oracle.com/javase/8/docs/technotes/guides/troubleshoot/memleaks002.html", "java.lang.OutOfMemoryError: GC overhead limit exceeded", "resource_exhaustion", ["GC overhead limit exceeded"]),
        ("java_metaspace", "Java Metaspace 溢出", "https://docs.oracle.com/javase/8/docs/technotes/guides/troubleshoot/memleaks002.html", "java.lang.OutOfMemoryError: Metaspace while loading classes", "resource_exhaustion", ["Metaspace"]),
        ("linux_too_many_files", "Linux 文件句柄耗尽", "https://man7.org/linux/man-pages/man2/open.2.html", "ERROR java.io.IOException: too many open files while accepting socket", "resource_exhaustion", ["too many open files"]),
        ("kubernetes_crashloopbackoff", "Kubernetes CrashLoopBackOff", "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/", "kubectl get pods shows app in CrashLoopBackOff. Back-off restarting failed container.", "kubernetes_pod_failure", ["CrashLoopBackOff"]),
        ("kubernetes_imagepullbackoff", "Kubernetes ImagePullBackOff", "https://kubernetes.io/docs/concepts/containers/images/", "Pod failed to start: ImagePullBackOff while pulling image.", "kubernetes_pod_failure", ["ImagePullBackOff"]),
        ("kubernetes_readiness_probe", "Kubernetes 探针失败", "https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/", "Pod failed readiness probe failed and kubelet keeps restarting the container.", "kubernetes_pod_failure", ["readiness probe failed"]),
        ("kubernetes_oomkilled", "Kubernetes OOMKilled", "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/", "Pod failed with reason OOMKilled after memory limit was exceeded.", "resource_exhaustion", ["OOMKilled"]),
        ("docker_container_exited", "Docker 容器退出", "https://docs.docker.com/reference/cli/docker/container/run/", "Docker container exited with code 137 immediately after startup.", "container_startup_failure", ["Docker"]),
        ("docker_entrypoint_failed", "Docker Entrypoint 失败", "https://docs.docker.com/reference/dockerfile/", "Docker container startup failed because entrypoint script returned error.", "container_startup_failure", ["Docker"]),
        ("docker_port_allocated", "Docker 端口映射冲突", "https://docs.docker.com/reference/cli/docker/container/run/", "Docker failed to start: port is already allocated for 0.0.0.0:8080.", "port_conflict", ["port is already allocated"]),
        ("docker_permission_denied", "Docker 权限拒绝", "https://docs.docker.com/engine/install/linux-postinstall/", "Docker error: permission denied while connecting to daemon socket.", "permission_and_auth", ["permission denied"]),
        ("disk_no_space", "磁盘空间不足", "https://www.kernel.org/doc/html/latest/filesystems/index.html", "ERROR failed to write log file: No space left on device.", "disk_and_filesystem", ["No space left on device"]),
        ("disk_readonly", "文件系统只读", "https://www.kernel.org/doc/html/latest/filesystems/index.html", "ERROR failed to write data: Read-only file system.", "disk_and_filesystem", ["Read-only file system"]),
        ("disk_quota", "磁盘配额耗尽", "https://www.kernel.org/doc/html/latest/filesystems/index.html", "ERROR upload failed: disk quota exceeded for application directory.", "disk_and_filesystem", ["disk quota exceeded"]),
        ("disk_usage_high", "磁盘使用率过高", "https://www.kernel.org/doc/html/latest/admin-guide/index.html", "WARN disk usage reached 98 percent and application failed to write logs.", "disk_and_filesystem", ["disk usage"]),
        ("dns_lookup_failed", "DNS 解析失败", "https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/", "DNS lookup failed for service payment: name or service not known.", "tls_dns_network", ["DNS lookup failed"]),
        ("tls_certificate_verify", "TLS 证书校验失败", "https://www.openssl.org/docs/", "SSL handshake failed: certificate verify failed while calling upstream API.", "tls_dns_network", ["SSL handshake"]),
        ("tls_handshake_failed", "TLS 握手失败", "https://www.openssl.org/docs/", "tls handshake failed when connecting to internal gateway.", "tls_dns_network", ["tls handshake failed"]),
        ("network_io_timeout", "网络 IO 超时", "https://docs.oracle.com/javase/8/docs/api/java/net/SocketTimeoutException.html", "java.net.SocketTimeoutException: Read timed out while calling remote service.", "timeout", ["Read timed out"]),
        ("redis_connection_refused", "Redis 连接拒绝", "https://redis.io/docs/latest/develop/clients/", "Redis connection failed: connection refused to 10.0.0.15:6379.", "connection_failure", ["connection refused"]),
        ("redis_timeout", "Redis 超时", "https://redis.io/docs/latest/develop/clients/", "Redis timeout while executing GET session: request timeout after 2000ms.", "connection_failure", ["Redis timeout"]),
        ("auth_unauthorized", "接口未授权", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401", "HTTP 401 Unauthorized when calling admin API.", "permission_and_auth", ["Unauthorized"]),
        ("auth_forbidden", "接口禁止访问", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403", "HTTP 403 Forbidden: access is denied for current user.", "permission_and_auth", ["Forbidden"]),
        ("config_invalid_property", "配置项无效", "https://docs.spring.io/spring-boot/reference/features/external-config.html", "Application failed to start because configuration property app.timeout is invalid.", "configuration_error", ["configuration property"]),
        ("timeout_connect", "连接超时", "https://docs.oracle.com/javase/8/docs/api/java/net/SocketTimeoutException.html", "connect timed out while opening socket to inventory service.", "timeout", ["connect timed out"]),
        ("timeout_request", "请求超时", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504", "request timeout after 30000ms when calling downstream service.", "timeout", ["request timeout"]),
        ("port_tomcat_bind", "Tomcat 端口绑定失败", "https://tomcat.apache.org/tomcat-10.1-doc/config/http.html", "Tomcat failed to start: java.net.BindException Address already in use: bind.", "port_conflict", ["Address already in use"]),
    ]
    return [
        _eval_case(
            f"external_{case_id}",
            f"{name}外部案例",
            "External annotated cases",
            url,
            f"根据{name}场景人工构造脱敏日志，并标注故障类型。",
            text,
            fault_type,
            evidence,
        )
        for case_id, name, url, text, fault_type, evidence in rows
    ]


def build_rag_cases() -> list[dict]:
    rows = [
        ("port_conflict", "端口冲突排查手册", ["APPLICATION FAILED TO START. Port 8080 was already in use.", "Tomcat failed to start: Address already in use."]),
        ("connection_failure", "连接失败排查手册", ["Communications link failure. Connection refused when connecting to MySQL.", "Redis connection failed: connection refused to 10.0.0.15:6379."]),
        ("gateway_5xx", "网关 5xx 错误排查手册", ["Nginx returned 502 Bad Gateway from upstream.", "Nginx upstream timed out, request returned 504 gateway timeout."]),
        ("timeout", "超时问题排查手册", ["Read timed out after 30000ms while calling payment service.", "connect timed out while opening socket to inventory service."]),
        ("resource_exhaustion", "资源耗尽排查手册", ["java.lang.OutOfMemoryError: Java heap space.", "too many open files while accepting new socket connection."]),
        ("configuration_error", "配置错误排查手册", ["Failed to bind properties under spring.datasource.", "Could not resolve placeholder DB_HOST."]),
        ("permission_and_auth", "权限与认证失败排查手册", ["Access denied for user app_user.", "HTTP 401 Unauthorized and 403 Forbidden when calling admin API."]),
        ("kubernetes_pod_failure", "Kubernetes Pod 异常排查手册", ["Pod is in CrashLoopBackOff.", "Pod failed to start: ImagePullBackOff while pulling image."]),
        ("container_startup_failure", "容器启动失败排查手册", ["Docker container exited with code 137.", "Container startup failed because entrypoint script returned error."]),
        ("database_slow_query", "数据库慢查询排查手册", ["Slow query detected. Full table scan happened on order table.", "SQL query took 18.5s rows_examined=1200000."]),
        ("disk_and_filesystem", "磁盘与文件系统排查手册", ["No space left on device. Application failed to write logs.", "Read-only file system prevented database from writing data files."]),
        ("tls_dns_network", "TLS、DNS 与网络排查手册", ["SSL handshake failed. certificate verify failed.", "DNS lookup failed for service payment: name or service not known."]),
    ]
    cases = []
    for fault_type, title, queries in rows:
        for index, query in enumerate(queries, start=1):
            cases.append(
                {
                    "id": f"rag_{fault_type}_{index}",
                    "name": f"{title}召回样本 {index}",
                    "query": query,
                    "fault_type": fault_type,
                    "expected_knowledge_titles": [title],
                    "k": 3,
                    "min_hits": 1,
                }
            )
    return cases


REPORT_PROFILES = {
    "port_conflict": {
        "title": "端口冲突排查手册",
        "source": "docs/knowledge/port_conflict.md",
        "component": "Web 服务端口",
        "cause": "日志中的 {term} 指向端口绑定失败，常见原因是旧进程、容器映射或本机服务占用了目标端口。",
        "step": "围绕 {term} 检查监听进程、服务启动参数和容器端口映射，确认冲突来源。",
        "fix": "处理 {term} 对应的端口占用后重启服务，可以释放占用进程或调整服务端口配置。",
        "prevention": "统一维护端口规划，并在发布前增加端口占用检查。",
    },
    "configuration_error": {
        "title": "配置错误排查手册",
        "source": "docs/knowledge/configuration_error.md",
        "component": "应用配置",
        "cause": "日志中的 {term} 指向配置解析或绑定失败，常见原因是环境变量缺失、配置项名称错误或格式不合法。",
        "step": "围绕 {term} 核对环境变量、配置文件和启动参数，确认线上实际加载的配置值。",
        "fix": "修正 {term} 对应配置后重新发布，并在启动阶段加入配置校验。",
        "prevention": "为关键配置增加模板、默认值说明和发布前校验。",
    },
    "connection_failure": {
        "title": "连接失败排查手册",
        "source": "docs/knowledge/connection_failure.md",
        "component": "下游连接",
        "cause": "日志中的 {term} 指向应用无法连接下游服务，可能是地址错误、服务未启动、防火墙或认证信息异常。",
        "step": "围绕 {term} 检查下游存活状态、网络连通性、连接池配置和账号权限。",
        "fix": "恢复 {term} 对应的下游访问路径，必要时修正地址、端口、账号或连接池参数。",
        "prevention": "为核心依赖增加健康检查、连接失败告警和降级策略。",
    },
    "database_slow_query": {
        "title": "数据库慢查询排查手册",
        "source": "docs/knowledge/database_slow_query.md",
        "component": "数据库",
        "cause": "日志中的 {term} 指向数据库执行耗时异常，可能存在全表扫描、索引缺失或返回数据量过大。",
        "step": "围绕 {term} 查看执行计划、索引命中情况、扫描行数和慢查询日志。",
        "fix": "优化 {term} 对应 SQL，可以补充索引、收敛查询条件或分页处理。",
        "prevention": "上线前评审高频 SQL，并对慢查询阈值和扫描行数建立告警。",
    },
    "gateway_5xx": {
        "title": "网关 5xx 错误排查手册",
        "source": "docs/knowledge/gateway_5xx.md",
        "component": "网关和 upstream 服务",
        "cause": "日志中的 {term} 指向网关访问 upstream 失败，常见原因是后端服务异常、连接被关闭或超时。",
        "step": "围绕 {term} 同时检查网关 access/error 日志、upstream 健康状态和应用错误日志。",
        "fix": "恢复 {term} 对应的 upstream 服务或调整网关超时、连接池和负载均衡配置。",
        "prevention": "为 upstream 增加健康探测、熔断和 5xx 比例告警。",
    },
    "resource_exhaustion": {
        "title": "资源耗尽排查手册",
        "source": "docs/knowledge/resource_exhaustion.md",
        "component": "应用资源",
        "cause": "日志中的 {term} 指向内存、文件句柄或容器资源达到限制，导致应用运行不稳定。",
        "step": "围绕 {term} 检查内存、GC、文件句柄、容器 limit 和进程资源使用情况。",
        "fix": "缓解 {term} 对应的资源瓶颈，可以扩容、调整 JVM 参数或修复资源泄漏。",
        "prevention": "补充资源水位告警、压测基线和容量评估。",
    },
    "kubernetes_pod_failure": {
        "title": "Kubernetes Pod 异常排查手册",
        "source": "docs/knowledge/kubernetes_pod_failure.md",
        "component": "Kubernetes Pod",
        "cause": "日志中的 {term} 指向 Pod 生命周期异常，可能与镜像拉取、探针、资源限制或启动命令有关。",
        "step": "围绕 {term} 查看 Pod events、容器日志、探针配置和资源限制。",
        "fix": "修复 {term} 对应的 Pod 启动条件，例如镜像、探针、资源 limit 或启动参数。",
        "prevention": "发布前校验镜像可拉取、探针可用和资源配置合理。",
    },
    "container_startup_failure": {
        "title": "容器启动失败排查手册",
        "source": "docs/knowledge/container_startup_failure.md",
        "component": "容器运行时",
        "cause": "日志中的 {term} 指向容器启动后异常退出，可能是入口脚本、端口、配置或资源限制问题。",
        "step": "围绕 {term} 查看容器退出码、启动命令、环境变量和最近一次容器日志。",
        "fix": "修复 {term} 对应的启动失败原因后重新拉起容器。",
        "prevention": "为镜像构建、启动脚本和运行参数增加发布前 smoke test。",
    },
    "permission_and_auth": {
        "title": "权限与认证失败排查手册",
        "source": "docs/knowledge/permission_and_auth.md",
        "component": "认证授权",
        "cause": "日志中的 {term} 指向认证或授权失败，可能是账号密码、Token、角色权限或访问策略不匹配。",
        "step": "围绕 {term} 核对调用方身份、权限配置、Token 状态和目标资源策略。",
        "fix": "修复 {term} 对应的认证凭据或授权规则，并避免在日志中暴露敏感信息。",
        "prevention": "为权限变更增加审批记录、最小权限校验和失败告警。",
    },
    "disk_and_filesystem": {
        "title": "磁盘与文件系统排查手册",
        "source": "docs/knowledge/disk_and_filesystem.md",
        "component": "磁盘和文件系统",
        "cause": "日志中的 {term} 指向磁盘或文件系统异常，可能是空间不足、只读挂载或配额耗尽。",
        "step": "围绕 {term} 检查磁盘使用率、inode、挂载状态和应用写入路径。",
        "fix": "处理 {term} 对应的磁盘问题，可以清理空间、扩容或修复挂载状态。",
        "prevention": "建立磁盘容量、inode 和只读挂载告警。",
    },
    "tls_dns_network": {
        "title": "TLS、DNS 与网络排查手册",
        "source": "docs/knowledge/tls_dns_network.md",
        "component": "网络访问",
        "cause": "日志中的 {term} 指向 TLS、DNS 或基础网络异常，可能是证书、域名解析或网络策略问题。",
        "step": "围绕 {term} 检查证书链、DNS 解析结果、网络策略和目标服务可达性。",
        "fix": "修复 {term} 对应的证书、域名或网络配置后重试调用。",
        "prevention": "为证书有效期、DNS 解析和网络连通性增加巡检。",
    },
    "timeout": {
        "title": "超时问题排查手册",
        "source": "docs/knowledge/timeout.md",
        "component": "远程调用",
        "cause": "日志中的 {term} 指向请求等待超过阈值，可能是下游变慢、网络抖动或超时配置不合理。",
        "step": "围绕 {term} 检查调用链耗时、下游负载、网络延迟和客户端超时配置。",
        "fix": "处理 {term} 对应的慢依赖或调整合理的超时、重试和降级策略。",
        "prevention": "增加 p95 延迟告警、依赖治理和超时参数基线。",
    },
}


def build_report_eval_cases() -> list[dict]:
    cases = []
    for raw_case in build_external_cases():
        term = raw_case["required_input_evidence"][0]
        profile = REPORT_PROFILES[raw_case["expected_fault_type"]]
        title = profile["title"]
        snippet = (
            profile["cause"].format(term=term)
            + " "
            + profile["step"].format(term=term)
            + " "
            + profile["fix"].format(term=term)
        )
        report_markdown = f"""## 1. 问题概述
- 故障类型：{raw_case["expected_fault_type"]}
- 严重等级：中
- 影响组件：{profile["component"]}
- 简要说明：{term} 导致当前服务诊断为 {raw_case["name"]}。

## 2. 关键信息提取
- 关键日志证据：{term}
- 输入摘要：{raw_case["input_text"]}

## 3. 可能原因分析
- {profile["cause"].format(term=term)}

## 4. 建议排查步骤
- {profile["step"].format(term=term)}

## 5. 修复建议
- {profile["fix"].format(term=term)}

## 6. 后续预防建议
- {profile["prevention"]}

## 7. 参考知识
- {title}：{snippet}
"""
        cases.append(
            {
                "id": raw_case["id"].replace("external_", "report_"),
                "name": raw_case["name"].replace("外部案例", "报告评估"),
                "input_summary": raw_case["input_text"],
                "report_markdown": report_markdown,
                "expected_fault_type": raw_case["expected_fault_type"],
                "expected_min_severity": "medium",
                "required_evidence": [term],
                "knowledge_refs": [
                    {
                        "title": title,
                        "source": profile["source"],
                        "snippet": snippet,
                    }
                ],
                "required_grounding_terms": [term],
                "min_key_evidence": 1,
                "min_possible_causes": 1,
                "min_troubleshooting_steps": 1,
                "min_fix_suggestions": 1,
                "min_prevention_suggestions": 1,
            }
        )

    return cases


def write_fixture(relative_path: str, cases: list[dict]) -> None:
    path = ROOT_DIR / relative_path
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{relative_path}: {len(cases)}")


def main() -> int:
    write_fixture("tests/fixtures/logmind_public_log_eval_cases.json", build_public_log_cases())
    write_fixture(
        "tests/fixtures/logmind_external_annotated_cases.json",
        build_external_cases(),
    )
    write_fixture("tests/fixtures/logmind_rag_eval_cases.json", build_rag_cases())
    write_fixture("tests/fixtures/logmind_report_eval_cases.json", build_report_eval_cases())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
