"""The machine-readable contract for ``contextcost --json``.

``--json`` existed before this module did, which was exactly the problem: the
Action, editor integrations and scripts were all invited to parse an output
whose shape was whatever the report happened to need that week. A format
nobody promises to keep still is not machine-readable, it is merely
machine-parseable today.

So the contract lives here, as data, in three pieces:

``SCHEMA_VERSION``
    An integer bumped only when a key changes meaning or disappears. Adding a
    new optional key does *not* bump it -- consumers must ignore keys they do
    not know, or every improvement becomes a breaking change.

``CONTRACT``
    Every top-level key, what it holds, and whether it is always present.
    ``--json-schema`` prints it; the test suite walks it against real output,
    so documentation that drifts from behaviour fails CI rather than a user's
    script.

``build_payload()``
    The one place a JSON response is assembled. The CLI calls nothing else,
    so the contract above cannot drift from what is printed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import used only for annotations
    from .accurate import AccurateResult
    from .reduce import Reduction
    from .walk import WalkResult

__all__ = ["CONTRACT", "SCHEMA_VERSION", "build_payload"]

#: Bump on breaking shape changes only. v1 is the first *promised* shape; the
#: pre-versioning output happened to match it, so nothing consumed before this
#: module existed needs to change.
SCHEMA_VERSION = 1

# Each entry: key -> (always present?, description). ``optional=True`` marks
# keys whose presence depends on flags (--accurate) rather than data.
CONTRACT: dict[str, dict[str, Any]] = {
    "schema": {
        "type": "integer",
        "desc": "this contract's version; see SCHEMA_VERSION",
    },
    "version": {
        "type": "string",
        "desc": "the contextcost release that produced this output",
    },
    "consumer": {
        "type": "string",
        "desc": "ignore-input model used: generic | cursor | aider | repomix",
    },
    "ignore_file": {
        "type": "string",
        "desc": "ignore file the proposal targets (.gitignore by default)",
    },
    "walk": {
        "type": "object",
        "desc": (
            "the measurement itself: root, consumer, ignore_files, tokens,"
            " bytes, files, text_files, binary_files, ignored, skipped[]"
        ),
    },
    "error_bound": {
        "type": "float",
        "desc": "measured relative error bound of the estimate (e.g. 0.14)",
    },
    "by_directory": {
        "type": "object[str -> int]",
        "desc": "estimated tokens per directory, descending",
    },
    "by_extension": {
        "type": "object[str -> int]",
        "desc": "estimated tokens per file extension, descending",
    },
    "largest": {
        "type": "array[object]",
        "desc": (
            "heaviest text files, each with path, bytes, tokens, kind, binary, sampled"
        ),
    },
    "reduction": {
        "type": "object",
        "desc": (
            "the propose-and-re-measure result: root, consumer, ignore_file,"
            " before, after, saved, share, measured, patterns[], excluded[],"
            " narrowed_from, findings[], deferred[]"
        ),
    },
    "accurate": {
        "type": "object",
        "optional": True,
        "desc": (
            "present only under --accurate: encoding, tokens,"
            " estimated_tokens, files[{path, tokens, estimated, sampled}],"
            " sampled_files[]"
        ),
    },
}


def _contract_text() -> str:
    lines = [f"contextcost --json schema v{SCHEMA_VERSION}", ""]
    for key, spec in CONTRACT.items():
        marker = "" if spec.get("optional") else " (always present)"
        lines.append(f"  {key}: {spec['type']}{marker}")
        lines.append(f"      {spec['desc']}")
    lines.append("")
    lines.append(
        "Stability: existing keys never change meaning within a schema"
        " version. New optional keys may appear without a bump -- ignore"
        " keys you do not know."
    )
    return "\n".join(lines)


def build_payload(
    *,
    version: str,
    consumer: str,
    reduction: Reduction,
    walk: WalkResult,
    error_bound: float,
    top: int,
    accurate: AccurateResult | None = None,
) -> dict:
    """Assemble the entire ``--json`` document. Nothing else prints JSON."""
    payload: dict = {
        "schema": SCHEMA_VERSION,
        "version": version,
        "consumer": consumer,
        "ignore_file": reduction.ignore_file,
        "walk": walk.as_dict(),
        "error_bound": error_bound,
        "by_directory": walk.by_directory(),
        "by_extension": walk.by_extension(),
        "largest": [cost.as_dict() for cost in walk.largest(top)],
        "reduction": reduction.as_dict(),
    }
    if accurate is not None:
        payload["accurate"] = accurate.as_dict()
    return payload
