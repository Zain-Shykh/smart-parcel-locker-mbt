import unittest
from locker.model import LockerModel, check_invariants, transition_universe
from locker.generators import ALL_GENERATORS
from locker.runner import SequenceRunner
from locker.mutants import MUTANTS
from locker.sut import ParcelLocker
from locker.types import Command as C, Operation as Op, State as S


class TestModel(unittest.TestCase):
    def test_lifecycle_and_rejection(self):
        m = LockerModel()
        self.assertTrue(m.step(C(Op.RESERVE, "C7")).accepted)
        before = m.snapshot()
        self.assertFalse(m.step(C(Op.DEPOSIT, code="WRONG")).accepted)
        self.assertEqual(m.snapshot(), before)
        self.assertTrue(m.step(C(Op.DEPOSIT, code="R-C7")).accepted)
        self.assertFalse(m.step(C(Op.DISABLE)).accepted)
        self.assertTrue(m.step(C(Op.RETRIEVE, code="P-C7")).accepted)
        self.assertFalse(m.step(C(Op.RETRIEVE, code="P-C7")).accepted)  # no double retrieval
        self.assertEqual(m.snapshot().state, S.AVAILABLE)

    def test_expire(self):
        m = LockerModel(); m.step(C(Op.RESERVE))
        self.assertFalse(m.step(C(Op.EXPIRE, expired=False)).accepted)
        self.assertTrue(m.step(C(Op.EXPIRE, expired=True)).accepted)
        self.assertEqual(m.snapshot().customer_id, None)

    def test_universe_size(self):
        s, t, p = transition_universe()
        self.assertEqual((len(s), len(t), len(p)), (4, 35, 305))

    def test_invariants_flag_bad_snapshot(self):
        sut = ParcelLocker(); sut.execute(C(Op.RESERVE)); sut.reservation_code = None
        self.assertTrue(check_invariants(sut.snapshot()))


class TestFramework(unittest.TestCase):
    def test_generators_reproducible_bounded_and_clean(self):
        for G in ALL_GENERATORS:
            a, b = G(3, 20).generate(30), G(3, 20).generate(30)
            self.assertEqual(a, b, G.name)
            self.assertTrue(all(1 <= len(s) <= 20 for s in a), G.name)
            self.assertTrue(all(SequenceRunner().run(s)["outcome"] == "PASS" for s in a), G.name)

    def test_every_nonequivalent_mutant_killed_by_each_strategy(self):
        for G in ALL_GENERATORS:
            seqs = G(1, 20).generate(200)
            for M in MUTANTS:
                killed = any(SequenceRunner(M).run(s)["outcome"] == "FAIL" for s in seqs)
                self.assertEqual(killed, not M.equivalent, f"{G.name} {M.name}")


if __name__ == "__main__":
    unittest.main()


class TestCrossProcessReproducibility(unittest.TestCase):
    def test_same_seed_same_sequences_across_hash_seeds(self):
        import subprocess, sys
        code = ("from locker.generators import ALL_GENERATORS;from locker.runner import fmt_seq;import hashlib;"
                "print(hashlib.md5(''.join(fmt_seq(s) for G in ALL_GENERATORS for s in G(1,20).generate(40)).encode()).hexdigest())")
        outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                               env={"PYTHONHASHSEED": h, "PATH": ""}).stdout for h in ("1", "2", "3")}
        self.assertEqual(len(outs), 1, outs)
