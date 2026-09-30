"""Versioned public schemas for AegisTrace boundaries."""

from aegistrace.schemas.agent_trace import (
    AgentTraceRecord,
    LessonVersion,
    SolutionEntry,
    SolutionKnowledge,
    TraceSourceReference,
)
from aegistrace.schemas.detections import (
    DetectionEvidence,
    DetectionResult,
    DetectionSeverity,
    DetectorType,
    detection_id_for,
)
from aegistrace.schemas.events import (
    AuthenticationEventDetails,
    CommandEventDetails,
    Ctu13FlowDetails,
    GenericEventDetails,
    GroundTruthLabel,
    HttpEventDetails,
    NetworkEventDetails,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.experiments import ExperimentArtifact, ExperimentRegistry, ExperimentRun
from aegistrace.schemas.manifests import DatasetManifest, ManifestFile, manifest_id_for

__all__ = [
    "AgentTraceRecord",
    "AuthenticationEventDetails",
    "CommandEventDetails",
    "Ctu13FlowDetails",
    "DatasetManifest",
    "DetectionEvidence",
    "DetectionResult",
    "DetectionSeverity",
    "DetectorType",
    "ExperimentArtifact",
    "ExperimentRegistry",
    "ExperimentRun",
    "GenericEventDetails",
    "GroundTruthLabel",
    "HttpEventDetails",
    "LessonVersion",
    "ManifestFile",
    "NetworkEventDetails",
    "SecurityEvent",
    "SolutionEntry",
    "SolutionKnowledge",
    "SourceRecordRef",
    "SourceType",
    "TraceSourceReference",
    "detection_id_for",
    "event_id_for",
    "manifest_id_for",
]
