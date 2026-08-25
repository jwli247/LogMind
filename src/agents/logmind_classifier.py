from schema import FaultType

_KEYWORDS: list[tuple[FaultType, tuple[str, ...]]] = [
    (
        FaultType.PORT_CONFLICT,
        (
            "port already in use",
            "port 8080 was already in use",
            "address already in use",
            "port is already allocated",
            "端口被占用",
            "端口占用",
        ),
    ),
    (
        FaultType.CONNECTION_FAILURE,
        (
            "communications link failure",
            "connection refused",
            "connection closed",
            "access denied for user",
            "could not connect to database",
            "database connection",
            "数据库连接失败",
            "无法连接数据库",
        ),
    ),
    (
        FaultType.CONNECTION_FAILURE,
        (
            "redis connection",
            "redis timeout",
            "jedisconnectionexception",
            "lettuceconnectionexception",
            "redis 连接失败",
            "redis 超时",
        ),
    ),
    (
        FaultType.GATEWAY_5XX,
        (
            "502 bad gateway",
            "504 gateway timeout",
            "upstream timed out",
            "connect() failed",
            "nginx 502",
            "网关超时",
        ),
    ),
    (
        FaultType.TIMEOUT,
        (
            "request timeout",
            "timeout",
            "timed out",
            "read timed out",
            "connect timed out",
            "connection timed out",
            "session timed out",
            "i/o timeout",
            "请求超时",
            "连接超时",
        ),
    ),
    (
        FaultType.RESOURCE_EXHAUSTION,
        (
            "outofmemoryerror",
            "out of memory",
            "java heap space",
            "gc overhead limit exceeded",
            "metaspace",
            "too many open files",
            "内存溢出",
            "oom",
        ),
    ),
    (
        FaultType.CONFIGURATION_ERROR,
        (
            "nullpointerexception",
            "cannot invoke",
            "空指针",
        ),
    ),
    (
        FaultType.DATABASE_SLOW_QUERY,
        (
            "sqlsyntaxerrorexception",
            "bad sql grammar",
            "syntax error",
            "duplicate entry",
            "sql 语法",
        ),
    ),
    (
        FaultType.CONFIGURATION_ERROR,
        (
            "failed to bind properties",
            "could not resolve placeholder",
            "configuration property",
            "配置错误",
            "配置文件",
        ),
    ),
    (
        FaultType.PERMISSION_AND_AUTH,
        (
            "permission denied",
            "access is denied",
            "client denied",
            "denied by server",
            "failed password",
            "authentication failure",
            "authentication failed",
            "unauthorized",
            "forbidden",
            "权限不足",
            "拒绝访问",
        ),
    ),
    (
        FaultType.KUBERNETES_POD_FAILURE,
        (
            "crashloopbackoff",
            "imagepullbackoff",
            "back-off restarting failed container",
            "pod failed",
            "pod 启动失败",
            "pod 循环重启",
        ),
    ),
    (
        FaultType.CONTAINER_STARTUP_FAILURE,
        (
            "docker",
            "container exited",
            "容器启动失败",
        ),
    ),
    (
        FaultType.DATABASE_SLOW_QUERY,
        (
            "slow query",
            "rows_examined",
            "query took",
            "took 18.5s",
            "慢查询",
            "查询很慢",
        ),
    ),
    (
        FaultType.DISK_AND_FILESYSTEM,
        (
            "no space left on device",
            "disk usage",
            "disk full",
            "read-only file system",
            "read-only",
            "disk quota exceeded",
            "磁盘空间不足",
            "磁盘满",
        ),
    ),
    (
        FaultType.TLS_DNS_NETWORK,
        (
            "dns lookup failed",
            "name or service not known",
            "tls handshake",
            "certificate verify failed",
            "ssl handshake",
            "dns 解析失败",
            "证书校验失败",
        ),
    ),
]

_DIAGNOSTIC_ERROR_HINTS: tuple[str, ...] = (
    "exception",
    "error",
    "failed",
    "failure",
    "timeout",
    "timed out",
    "refused",
    "connection closed",
    "denied",
    "unauthorized",
    "forbidden",
    "authentication failure",
    "authentication failed",
    "traceback",
    "stack trace",
    "caused by",
    "application failed to start",
    "outofmemory",
    "oomkilled",
    "nullpointer",
    "sqlsyntax",
    "slow query",
    "rows_examined",
    "bad gateway",
    "gateway timeout",
    "crashloopbackoff",
    "imagepullbackoff",
    "container exited",
    "no space left on device",
    "dns lookup failed",
    "tls handshake",
    "报错",
    "异常",
    "错误",
    "失败",
    "超时",
    "拒绝连接",
    "拒绝访问",
    "内存溢出",
    "空指针",
)

_DIAGNOSTIC_COMPONENT_HINTS: tuple[str, ...] = (
    "spring boot",
    "mysql",
    "redis",
    "nginx",
    "docker",
    "kubernetes",
    "k8s",
    "jvm",
    "tomcat",
    "gateway",
    "database",
    "数据库",
    "网关",
    "容器",
    "服务",
    "端口",
)

_DIAGNOSTIC_ACTION_HINTS: tuple[str, ...] = (
    "启动失败",
    "连接失败",
    "连接超时",
    "无法连接",
    "无法启动",
    "端口占用",
    "端口被占用",
    "排查",
    "分析日志",
    "分析这段",
    "定位问题",
    "故障",
    "日志",
    "堆栈",
)

_MIN_DIAGNOSTIC_LENGTH = 20


def is_diagnostic_request(text: str) -> bool:
    normalized = text.lower().strip()
    if not normalized:
        return False

    if any(hint in normalized for hint in _DIAGNOSTIC_ERROR_HINTS):
        return True

    has_component = any(hint in normalized for hint in _DIAGNOSTIC_COMPONENT_HINTS)
    has_action = any(hint in normalized for hint in _DIAGNOSTIC_ACTION_HINTS)
    if has_component and has_action:
        return True

    if len(normalized) >= _MIN_DIAGNOSTIC_LENGTH and has_action:
        return True

    return False


def classify_fault_type(text: str) -> FaultType:
    normalized = text.lower()

    priority_keywords: tuple[tuple[FaultType, tuple[str, ...]], ...] = (
        (
            FaultType.TLS_DNS_NETWORK,
            (
                "dns lookup failed",
                "name or service not known",
                "tls handshake",
                "certificate verify failed",
                "ssl handshake",
            ),
        ),
        (
            FaultType.CONFIGURATION_ERROR,
            (
                "failed to bind properties",
                "could not resolve placeholder",
                "configuration property",
            ),
        ),
    )
    for fault_type, keywords in priority_keywords:
        if any(keyword in normalized for keyword in keywords):
            return fault_type

    for fault_type, keywords in _KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return fault_type

    return FaultType.UNKNOWN
