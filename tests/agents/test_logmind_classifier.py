import pytest

from agents.logmind_classifier import classify_fault_type
from schema import FaultType


@pytest.mark.parametrize(
    ("log_text", "expected"),
    [
        (
            "Web server failed to start. Port 8080 was already in use.",
            FaultType.PORT_CONFLICT,
        ),
        (
            "java.sql.SQLNonTransientConnectionException: Communications link failure",
            FaultType.CONNECTION_FAILURE,
        ),
        (
            "redis.clients.jedis.exceptions.JedisConnectionException: Redis connection failed",
            FaultType.CONNECTION_FAILURE,
        ),
        (
            "upstream timed out while reading response header from upstream, 504 gateway timeout",
            FaultType.GATEWAY_5XX,
        ),
        (
            "java.lang.OutOfMemoryError: Java heap space",
            FaultType.RESOURCE_EXHAUSTION,
        ),
        (
            "java.lang.NullPointerException: Cannot invoke because user is null",
            FaultType.CONFIGURATION_ERROR,
        ),
        (
            "SQLSyntaxErrorException: You have an error in your SQL syntax",
            FaultType.DATABASE_SLOW_QUERY,
        ),
        (
            "Failed to bind properties under server.port to java.lang.Integer",
            FaultType.CONFIGURATION_ERROR,
        ),
        (
            "Permission denied: access is denied",
            FaultType.PERMISSION_AND_AUTH,
        ),
        (
            "Docker container exited with code 1",
            FaultType.CONTAINER_STARTUP_FAILURE,
        ),
    ],
)
def test_classify_fault_type_known_patterns(log_text: str, expected: FaultType) -> None:
    assert classify_fault_type(log_text) == expected


def test_classify_fault_type_is_case_insensitive() -> None:
    log_text = "APPLICATION FAILED TO START. ADDRESS ALREADY IN USE."

    assert classify_fault_type(log_text) == FaultType.PORT_CONFLICT


def test_classify_fault_type_returns_unknown_for_unmatched_text() -> None:
    log_text = "The application printed a normal startup banner."

    assert classify_fault_type(log_text) == FaultType.UNKNOWN
