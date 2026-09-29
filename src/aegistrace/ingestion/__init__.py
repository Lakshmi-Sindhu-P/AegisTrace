"""Source adapters and ingestion reports."""

from aegistrace.ingestion.ctu13 import (
    CTU13_ADAPTER_VERSION,
    CTU13_DATASET_NAME,
    CTU13_TRANSFORMATION_VERSION,
    parse_ctu13_binetflow,
    write_ctu13_ingestion_outputs,
)
from aegistrace.ingestion.iot23 import (
    IOT23_ADAPTER_VERSION,
    IOT23_DATASET_NAME,
    IOT23_TRANSFORMATION_VERSION,
    parse_iot23_conn_log,
    write_ingestion_outputs,
)
from aegistrace.ingestion.report import IngestionReport, ParseIssue, ParseResult

__all__ = [
    "CTU13_ADAPTER_VERSION",
    "CTU13_DATASET_NAME",
    "CTU13_TRANSFORMATION_VERSION",
    "IOT23_ADAPTER_VERSION",
    "IOT23_DATASET_NAME",
    "IOT23_TRANSFORMATION_VERSION",
    "IngestionReport",
    "ParseIssue",
    "ParseResult",
    "parse_ctu13_binetflow",
    "parse_iot23_conn_log",
    "write_ctu13_ingestion_outputs",
    "write_ingestion_outputs",
]
