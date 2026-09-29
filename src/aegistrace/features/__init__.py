"""Versioned, leakage-reviewed feature builders."""

from aegistrace.features.network import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    FeatureDataset,
    FeatureRecord,
    build_ctu13_features,
    write_feature_parquet,
)

__all__ = [
    "FEATURE_NAMES",
    "FEATURE_VERSION",
    "FeatureDataset",
    "FeatureRecord",
    "build_ctu13_features",
    "write_feature_parquet",
]
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    CAUSAL_FEATURE_VERSION,
    CausalFeatureDataset,
    CausalFeatureRecord,
    audit_causal_prior_window,
    build_ctu13_causal_features,
    write_causal_feature_parquet,
)

__all__ = [
    "CAUSAL_FEATURE_NAMES",
    "CAUSAL_FEATURE_VERSION",
    "CausalFeatureDataset",
    "CausalFeatureRecord",
    "audit_causal_prior_window",
    "build_ctu13_causal_features",
    "write_causal_feature_parquet",
]
