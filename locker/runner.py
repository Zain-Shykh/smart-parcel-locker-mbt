"""Automated execution + oracle. Fresh SUT and model per sequence; compares Result and the
complete Snapshot after every command, checks invariants on the SUT snapshot, and checks that
rejected commands leave the SUT snapshot untouched (independent of the model)."""
from .model import LockerModel, check_invariants
from .sut import ParcelLocker
from .types import Command


def fmt_cmd(c: Command) -> str:
    return f"{c.operation.value}(cust={c.customer_id},code={c.code!r},expired={c.expired})"


def fmt_seq(seq) -> str:
    return " ; ".join(fmt_cmd(c) for c in seq)


class SequenceRunner:
    def __init__(self, sut_factory=ParcelLocker, model_factory=LockerModel):
        self.sut_factory, self.model_factory = sut_factory, model_factory

    def run(self, sequence, test_id="", strategy=""):
        sut, model = self.sut_factory(), self.model_factory()
        rec = dict(test_id=test_id, strategy=strategy, sequence=fmt_seq(sequence), length=len(sequence),
                   initial_state=sut.snapshot().state.value, expected_result="", actual_result="",
                   expected_final="", actual_final="", outcome="PASS", fail_index=-1, failure_details="")
        trace, failed = [], False
        for i, cmd in enumerate(sequence):
            before = sut.snapshot() if not failed else None
            exp = model.step(cmd)
            trace.append(model.last)
            if failed:
                continue  # keep stepping the model so the coverage trace covers the whole sequence
            try:
                act = sut.execute(cmd)
                after = sut.snapshot()
            except Exception as e:  # SUT crash is a failure, not a framework error
                act, after = None, None
                problems = [f"SUT raised {type(e).__name__}: {e}"]
            else:
                problems = []
                if (act.accepted, act.message) != (exp.accepted, exp.message):
                    problems.append(f"result expected {exp} got {act}")
                if after != model.snapshot():
                    problems.append(f"snapshot expected {model.snapshot()} got {after}")
                problems += [f"invariant violated: {v}" for v in check_invariants(after)]
                if not act.accepted and after != before:
                    problems.append("rejected command mutated SUT state")
            rec["expected_result"], rec["actual_result"] = str(exp), str(act)
            rec["expected_final"] = str(model.snapshot())
            rec["actual_final"] = str(after)
            if problems:
                failed = True
                rec.update(outcome="FAIL", fail_index=i,
                           failure_details=f"step {i} {fmt_cmd(cmd)}: " + " | ".join(problems))
        if not failed:
            rec["expected_final"] = rec["actual_final"] = str(model.snapshot())
        rec["trace"] = trace
        return rec
