"""Pure transport partitioning for a predeclared, ordered evaluation.

This module performs no I/O and imports no runner or provider client. It assigns
the first 1,000 tasks to the supplied core phase and all remaining tasks to the
supplied extension phase. Membership, protocol and payment authorization belong
to the caller.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

Task = TypeVar('Task')
CORE_SIZE = 1000
MAX_CHUNK_SIZE = 1000


def partition_tasks(
    tasks: Sequence[Task],
    *,
    core_phase: str,
    extension_phase: str,
    schedule: Sequence[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Return ``{'phase': name, 'tasks': [...]}`` stages in original order.

    Each schedule pair is an increasing cumulative endpoint and the maximum
    chunk size for that segment. Endpoints are exclusive, zero-based positions;
    for example ``[(3000, 100), (4000, 50), (4600, 25), (4800, 5)]``
    partitions 4,800 tasks. The final endpoint must equal ``len(tasks)``.
    A chunk ends early at its segment endpoint or at the core boundary, so no
    stage crosses position 1,000. Chunk sizes must be integers from 1 to 1,000.

    Stage lists are new lists. Task objects and their metadata are retained
    unchanged; this function neither copies nor edits individual task objects.
    """
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes, bytearray)):
        raise ValueError('Tasks must be an ordered sequence')
    if not tasks:
        raise ValueError('Tasks must be nonempty')
    if (not isinstance(core_phase, str) or not core_phase.strip()
            or not isinstance(extension_phase, str) or not extension_phase.strip()
            or core_phase == extension_phase):
        raise ValueError('Core and extension phase names must be nonempty and distinct')
    if (not isinstance(schedule, Sequence)
            or isinstance(schedule, (str, bytes, bytearray)) or not schedule):
        raise ValueError('Schedule must be a nonempty ordered sequence of endpoint/chunk pairs')

    segments = []
    previous = 0
    for pair in schedule:
        if (not isinstance(pair, Sequence) or isinstance(pair, (str, bytes, bytearray))
                or len(pair) != 2):
            raise ValueError('Each schedule entry must contain an endpoint and a chunk size')
        endpoint, chunk = pair
        if type(endpoint) is not int or endpoint <= previous:
            raise ValueError('Cumulative endpoints must be strictly increasing positive integers')
        if endpoint > len(tasks):
            raise ValueError('A cumulative endpoint exceeds the fixed task count')
        if type(chunk) is not int or not 1 <= chunk <= MAX_CHUNK_SIZE:
            raise ValueError('Chunk sizes must be integers from 1 to 1000')
        segments.append((endpoint, chunk))
        previous = endpoint
    if previous != len(tasks):
        raise ValueError('The final endpoint must equal the fixed task count')

    stages = []
    start = 0
    for endpoint, chunk in segments:
        while start < endpoint:
            stop = min(start + chunk, endpoint)
            if start < CORE_SIZE:
                stop = min(stop, CORE_SIZE)
            stages.append({'phase': core_phase if start < CORE_SIZE else extension_phase,
                           'tasks': list(tasks[start:stop])})
            start = stop
    return stages
