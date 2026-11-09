"""Short demo: model run -> generation -> execution -> injected fault detection.  python demo.py"""
from locker.generators import TransitionPairGenerator
from locker.model import LockerModel
from locker.mutants import M05_StaleRetrievalCode
from locker.runner import SequenceRunner, fmt_cmd
from locker.types import Command as C, Operation as Op

m = LockerModel()
for c in [C(Op.RESERVE, "C1"), C(Op.DEPOSIT, code="WRONG"), C(Op.DEPOSIT, code="R-C1"), C(Op.RETRIEVE, code="P-C1")]:
    print("model:", fmt_cmd(c), "->", m.step(c), m.snapshot().state.value)
seqs = TransitionPairGenerator(seed=1, max_length=20).generate(20)
print("generated", len(seqs), "sequences; first:", [c.operation.value for c in seqs[0]])
print("reference SUT failures:", sum(SequenceRunner().run(s)["outcome"] == "FAIL" for s in seqs))
for i, s in enumerate(seqs):
    r = SequenceRunner(M05_StaleRetrievalCode).run(s, f"t{i}", "transition_pair")
    if r["outcome"] == "FAIL":
        print("MUTANT", M05_StaleRetrievalCode.name, "KILLED by", r["test_id"], "\n ", r["failure_details"]); break
