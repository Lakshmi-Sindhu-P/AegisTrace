"""Serve the local AegisTrace UI on the loopback interface only.

The UI is an investigation instrument for one analyst on one machine. It is not a service. This
entry point therefore binds ``127.0.0.1`` and **refuses to bind anything else** - there is no flag
to expose it, because "localhost-only" is an approved security constraint of this project rather
than a default that a caller may override.

Why the refusal is structural rather than documented: a documented-only constraint is enforced by
whoever reads the documentation. A host that is not the loopback address is rejected here, so the
instrument cannot be put on a network interface by passing an argument.

Usage:

    .venv/bin/python scripts/run_local_ui.py \
        --artifact data/evaluation/triage_spine/offline_spine_demo.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

#: The only host this server may bind. See the module docstring for why this is not configurable.
LOOPBACK = "127.0.0.1"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        default="data/evaluation/triage_spine/offline_spine_demo.json",
        help="Spine summary to read. Must already exist; the UI never produces it.",
    )
    parser.add_argument("--port", type=int, default=8765, help="Loopback port to listen on.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.port < 1 or args.port > 65535:
        print(f"run_local_ui: port out of range: {args.port}", file=sys.stderr)
        return 2

    artifact = Path(args.artifact)
    if not artifact.is_absolute():
        artifact = REPO_ROOT / artifact
    if not artifact.exists():
        # Refuse before binding a socket. A server that starts and then shows "artifact unavailable"
        # is worse than one that never starts, because the operator believes it is working.
        print(
            f"run_local_ui: artifact not found: {artifact}\n"
            f"  produce it first, for example:\n"
            f"    .venv/bin/python scripts/run_offline_spine_demo.py "
            f"--created-at 2026-10-08T13:00:00Z",
            file=sys.stderr,
        )
        return 2

    try:
        import uvicorn
    except ModuleNotFoundError:
        print(
            "run_local_ui: the UI extra is not installed.\n"
            "  install it with:  uv pip install -e '.[ui]'   (or: pip install -e '.[ui]')",
            file=sys.stderr,
        )
        return 2

    from aegistrace.ui.app import create_app

    app = create_app(artifact_path=artifact)
    print(f"run_local_ui: serving http://{LOOPBACK}:{args.port}/ (loopback only)")
    print(f"run_local_ui: reading {artifact}")
    uvicorn.run(app, host=LOOPBACK, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
