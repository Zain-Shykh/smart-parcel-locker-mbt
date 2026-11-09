"""Three genuinely different test-generation strategies over the executable model.

A  RandomWalkGenerator        - no feedback: uniform random choice of operation, then of its input.
B  CoverageGuidedGenerator    - greedy feedback on global transition/state coverage (one-step lookahead).
C  TransitionPairGenerator    - plans: BFS path to a *specific uncovered transition pair*, then greedy pair fill.

Each generator: seeded `random.Random`, `generate(count) -> list[list[Command]]`,
sequence length bounded by `max_length`, valid and invalid commands both produced.
"""
import random
from collections import Counter

from .model import LockerModel, candidate_commands, find_path, transition_universe
from .types import Operation


class _Base:
    def __init__(self, seed: int, max_length: int):
        self.seed, self.max_length = seed, max_length
        self.rng = random.Random(seed)


class RandomWalkGenerator(_Base):
    """Operation chosen uniformly from the 8 operations (so rare ops are not drowned by
    input variants), then input variant uniformly. Length uniform in [1, max_length].
    Model is used only to craft the 'correct' credential; there is no coverage feedback."""
    name = "random_walk"

    def generate(self, count: int):
        out = []
        for _ in range(count):
            m, seq = LockerModel(), []
            for _ in range(self.rng.randint(1, self.max_length)):
                by_op = {}
                for c in candidate_commands(m):
                    by_op.setdefault(c.operation, []).append(c)
                cmd = self.rng.choice(by_op[self.rng.choice(list(Operation))])
                m.step(cmd); seq.append(cmd)
            out.append(seq)
        return out


class CoverageGuidedGenerator(_Base):
    """Greedy: at each step peek every candidate's transition; pick randomly among those whose
    transition is globally uncovered, else the least-executed transition (ties random).
    Coverage counters persist across the whole generate() call, so later sequences
    are pushed toward the under-exercised parts of the model."""
    name = "coverage_guided"

    def generate(self, count: int):
        hits, out = Counter(), []
        for _ in range(count):
            m, seq = LockerModel(), []
            for _ in range(self.rng.randint(1, self.max_length)):
                scored = [(hits[m.peek(c)], c) for c in candidate_commands(m)]
                best = min(s for s, _ in scored)
                cmd = self.rng.choice([c for s, c in scored if s == best])
                m.step(cmd); hits[m.last] += 1; seq.append(cmd)
            out.append(seq)
        return out


class TransitionPairGenerator(_Base):
    """Per sequence: choose an uncovered transition pair (t1,t2) at random, plan the shortest
    command path that reaches t1 (BFS on the model), execute t1 then t2, then keep extending
    greedily with commands that complete further uncovered pairs. Once all pairs are covered it
    degrades to pair-count-balanced exploration."""
    name = "transition_pair"

    def generate(self, count: int):
        _, _, pairs = transition_universe()
        hits = Counter({p: 0 for p in pairs})
        out = []
        for _ in range(count):
            uncovered = sorted((p for p in pairs if hits[p] == 0), key=repr)
            target = self.rng.choice(uncovered) if uncovered else self.rng.choice(sorted(pairs, key=repr))
            m, seq, prev = LockerModel(), [], None
            plan = find_path(m, target=target[0]) or []
            tail = find_path_after(m, plan, target[1])
            budget = self.max_length
            for c in (plan + tail)[:budget]:
                prev = self._do(m, c, seq, prev, hits)
            length = self.rng.randint(len(seq), self.max_length)
            while len(seq) < length:
                scored = [(hits[(prev, m.peek(c))] if prev else 0, c) for c in candidate_commands(m)]
                best = min(s for s, _ in scored)
                prev = self._do(m, self.rng.choice([c for s, c in scored if s == best]), seq, prev, hits)
            out.append(seq)
        return out

    @staticmethod
    def _do(m, cmd, seq, prev, hits):
        m.step(cmd); seq.append(cmd)
        if prev is not None:
            hits[(prev, m.last)] += 1
        return m.last


def find_path_after(model, prefix, target):
    """Replay `prefix` on a clone of `model`, then find the command realising `target`."""
    m = model.clone()
    for c in prefix:
        m.step(c)
    return find_path(m, target=target) or []


ALL_GENERATORS = [RandomWalkGenerator, CoverageGuidedGenerator, TransitionPairGenerator]
