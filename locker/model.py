"""Independent executable state-machine model (oracle), derived from data/requirements.md only.

Design notes (see REPORT.md section 3):
* decide-then-apply: `_decide` is pure (no mutation); `_apply` runs only for accepted
  commands. Rule 12 (rejected => no mutation) therefore holds by construction, and the
  model is structured differently from the SUT's inline if/mutate style.
* Reject precedence (assumption A1): state check first, then credential, then expiry flag.
* Every step records a `Transition` label (src, op, outcome, dst) used for coverage.
"""
import copy
from collections import namedtuple, deque

from .types import Command, Operation as Op, Result, Snapshot, State as S

Transition = namedtuple("Transition", "src op outcome dst")

OTHER = {"C1": "C2"}  # cross-customer credential helper for the input alphabet


class LockerModel:
    def __init__(self):
        self.reset()

    def reset(self):
        self._state = S.AVAILABLE
        self._customer = None
        self._res_code = None
        self._ret_code = None
        self.last = None  # last Transition

    # ---- specification -------------------------------------------------
    def _decide(self, c: Command):
        s, op = self._state, c.operation
        if op == Op.INVALID_ACCESS:
            return False, "invalid_access"
        if op == Op.RESERVE:
            return (True, "reserved") if s == S.AVAILABLE else (False, "locker_not_available")
        if op == Op.CANCEL:
            return (True, "cancelled") if s == S.RESERVED else (False, "not_reserved")
        if op == Op.DEPOSIT:
            if s != S.RESERVED:
                return False, "not_reserved"
            return (True, "deposited") if c.code == self._res_code else (False, "invalid_reservation_code")
        if op == Op.RETRIEVE:
            if s != S.OCCUPIED:
                return False, "no_parcel"
            return (True, "retrieved") if c.code == self._ret_code else (False, "invalid_retrieval_code")
        if op == Op.EXPIRE:
            if s != S.RESERVED:
                return False, "not_reserved"
            return (True, "expired") if c.expired else (False, "not_expired")
        if op == Op.DISABLE:
            return (True, "disabled") if s == S.AVAILABLE else (False, "cannot_disable")
        if op == Op.ENABLE:
            return (True, "enabled") if s == S.MAINTENANCE else (False, "not_in_maintenance")
        return False, "unknown_operation"

    def _apply(self, c: Command):
        op = c.operation
        if op == Op.RESERVE:
            self._state, self._customer, self._res_code = S.RESERVED, c.customer_id, f"R-{c.customer_id}"
        elif op == Op.DEPOSIT:
            self._state, self._ret_code = S.OCCUPIED, f"P-{self._customer}"
        elif op in (Op.CANCEL, Op.RETRIEVE, Op.EXPIRE):  # rules 3, 7, 8: back to AVAILABLE, wipe data
            self._state, self._customer, self._res_code, self._ret_code = S.AVAILABLE, None, None, None
        elif op == Op.DISABLE:
            self._state = S.MAINTENANCE
        elif op == Op.ENABLE:
            self._state = S.AVAILABLE

    def step(self, command: Command) -> Result:
        src = self._state
        ok, msg = self._decide(command)
        if ok:
            self._apply(command)
        self.last = Transition(src, command.operation, msg, self._state)
        return Result(ok, msg)

    def snapshot(self) -> Snapshot:
        return Snapshot(self._state, self._customer, self._res_code, self._ret_code)

    def clone(self):
        return copy.deepcopy(self)

    def peek(self, command: Command) -> Transition:
        """Transition the command would take, without changing this model."""
        m = self.clone()
        m.step(command)
        return m.last


# ---- invariants (checked by the oracle on the SUT snapshot) --------------
def check_invariants(s: Snapshot):
    """State invariants derived from the requirements; returns list of violations."""
    v = []
    if s.state in (S.AVAILABLE, S.MAINTENANCE):
        if (s.customer_id, s.reservation_code, s.retrieval_code) != (None, None, None):
            v.append(f"INV1 {s.state.value} must hold no customer/credential data")
    if s.state == S.RESERVED:
        if s.customer_id is None or s.reservation_code != f"R-{s.customer_id}":
            v.append("INV2 RESERVED requires customer and reservation code R-<customer>")
        if s.retrieval_code is not None:
            v.append("INV3 RESERVED must not hold a retrieval code")
    if s.state == S.OCCUPIED:
        if s.customer_id is None or s.retrieval_code != f"P-{s.customer_id}":
            v.append("INV4 OCCUPIED requires customer and retrieval code P-<customer>")
    return v


# ---- input alphabet and coverage universe --------------------------------
def candidate_commands(m: LockerModel):
    """All commands (valid and invalid) worth trying from the model's current situation."""
    snap = m.snapshot()
    cust = snap.customer_id or "C1"
    other = OTHER.get(cust, "C1")
    cmds = [Command(Op.RESERVE, c) for c in ("C1", "C2")]
    cmds.append(Command(Op.CANCEL))
    for code in {snap.reservation_code or "R-C1", "WRONG", f"P-{cust}", f"R-{other}"}:
        cmds.append(Command(Op.DEPOSIT, customer_id=cust, code=code))
    for code in {snap.retrieval_code or "P-C1", "WRONG", f"R-{cust}", f"P-{other}"}:
        cmds.append(Command(Op.RETRIEVE, customer_id=cust, code=code))
    cmds += [Command(Op.EXPIRE, expired=True), Command(Op.EXPIRE, expired=False),
             Command(Op.DISABLE), Command(Op.ENABLE), Command(Op.INVALID_ACCESS, code="BAD")]
    return cmds


def find_path(start: LockerModel, target: Transition = None, goal_state=None):
    """BFS over (model snapshot) using the alphabet; shortest command list whose last
    step yields `target` (or, if goal_state, that leaves the model in goal_state)."""
    seen, q = {start.snapshot().__repr__()}, deque([(start, [])])
    while q:
        m, path = q.popleft()
        if goal_state is not None and m.snapshot().state == goal_state:
            return path
        for c in candidate_commands(m):
            t = m.peek(c)
            if target is not None and t == target:
                return path + [c]
            n = m.clone(); n.step(c)
            key = repr(n.snapshot())
            if key not in seen:
                seen.add(key); q.append((n, path + [c]))
    return None


def transition_universe():
    """(states, transitions, pairs): all model transitions reachable from the initial state.
    A transition pair (t1,t2) is defined iff t1.dst == t2.src (adjacent in some execution)."""
    seen, q, trans = set(), deque([LockerModel()]), set()
    while q:
        m = q.popleft()
        key = repr(m.snapshot())
        if key in seen:
            continue
        seen.add(key)
        for c in candidate_commands(m):
            t = m.peek(c); trans.add(t)
            n = m.clone(); n.step(c); q.append(n)
    pairs = {(a, b) for a in trans for b in trans if a.dst == b.src}
    return set(S), trans, pairs
