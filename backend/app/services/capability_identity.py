"""Deterministic, content-addressed IDs for the append-only capability tables — Program Engine
v5 Milestone 2. Replaces check-then-insert with a database-enforced uniqueness guarantee: two
callers computing the same logical identity always compute the same id, so a race resolves via
a harmless insert-or-ignore rather than an application-level check that can lose a race.

See the Milestone 2 v2.2 plan, §D5, for the identity tuple each table uses. This module only
defines the hashing primitive — each service module defines its own table-specific identity
tuple and calls `deterministic_id` with it.
"""

import uuid

# Fixed namespace — arbitrary but constant, so the same (table, parts) tuple always hashes to
# the same UUID across processes and runs. Never regenerate this value.
_NAMESPACE = uuid.UUID("6f1f6e2a-3b8b-4f0a-9b7a-4b6b8a2c9d3e")


def deterministic_id(table_name: str, *parts: object) -> str:
    """uuid5(NAMESPACE, "table_name|part1|part2|...") — stable across processes and runs.
    Every part is str()'d, so callers must pass values whose str() representation is itself
    stable and meaningful (e.g. a real sentinel string, never a bare None)."""
    key = "|".join([table_name, *(str(p) for p in parts)])
    return str(uuid.uuid5(_NAMESPACE, key))
