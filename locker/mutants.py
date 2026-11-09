"""Fourteen mutants of the reference SUT, each a distinct plausible defect.
`equivalent=True` marks mutants proven (by reasoning) to be unobservable."""
from .sut import ParcelLocker
from .types import Operation as Op, Result, State as S


class _M(ParcelLocker):
    name = desc = ""
    equivalent = False

    def execute(self, c):
        r = self.mutate(c)
        return r if r is not None else super().execute(c)

    def mutate(self, c):  # return Result to override, None to fall through to the reference
        return None


class M01_ReserveWhenOccupied(_M):
    name, desc = "M01_reserve_when_occupied", "RESERVE accepted in OCCUPIED (overwrites parcel owner)"
    def mutate(self, c):
        if c.operation == Op.RESERVE and self.state == S.OCCUPIED:
            self.state, self.customer_id = S.RESERVED, c.customer_id
            self.reservation_code, self.retrieval_code = f"R-{c.customer_id}", None
            return Result(True, "reserved")

class M02_DepositInMaintenance(_M):
    name, desc = "M02_deposit_in_maintenance", "DEPOSIT accepted during MAINTENANCE"
    def mutate(self, c):
        if c.operation == Op.DEPOSIT and self.state == S.MAINTENANCE:
            self.state, self.retrieval_code = S.OCCUPIED, f"P-{self.customer_id}"
            return Result(True, "deposited")

class M03_RetrieveNoAuth(_M):
    name, desc = "M03_retrieve_no_auth", "RETRIEVE accepted with any code"
    def mutate(self, c):
        if c.operation == Op.RETRIEVE and self.state == S.OCCUPIED:
            self._clear(); return Result(True, "retrieved")

class M04_ExpireIgnoresFlag(_M):
    name, desc = "M04_expire_ignores_flag", "EXPIRE accepted although expired=False"
    def mutate(self, c):
        if c.operation == Op.EXPIRE and self.state == S.RESERVED:
            self._clear(); return Result(True, "expired")

class M05_StaleRetrievalCode(_M):
    name, desc = "M05_stale_retrieval_code", "retrieval code kept after successful RETRIEVE"
    def mutate(self, c):
        if c.operation == Op.RETRIEVE and self.state == S.OCCUPIED and c.code == self.retrieval_code:
            code = self.retrieval_code; self._clear(); self.retrieval_code = code
            return Result(True, "retrieved")

class M06_CancelWhenOccupied(_M):
    name, desc = "M06_cancel_when_occupied", "CANCEL accepted in OCCUPIED (parcel lost)"
    def mutate(self, c):
        if c.operation == Op.CANCEL and self.state == S.OCCUPIED:
            self._clear(); return Result(True, "cancelled")

class M07_BadDepositMutates(_M):
    name, desc = "M07_bad_deposit_mutates", "wrong-code DEPOSIT erases the reservation code but is rejected"
    def mutate(self, c):
        if c.operation == Op.DEPOSIT and self.state == S.RESERVED and c.code != self.reservation_code:
            self.reservation_code = None; return Result(False, "invalid_reservation_code")

class M08_DisableWhenReserved(_M):
    name, desc = "M08_disable_when_reserved", "DISABLE accepted in RESERVED"
    def mutate(self, c):
        if c.operation == Op.DISABLE and self.state == S.RESERVED:
            self.state = S.MAINTENANCE; return Result(True, "disabled")

class M09_EnableWhenAvailable(_M):
    name, desc = "M09_enable_when_available", "ENABLE accepted in AVAILABLE"
    def mutate(self, c):
        if c.operation == Op.ENABLE and self.state == S.AVAILABLE:
            return Result(True, "enabled")

class M10_InvalidAccessCancels(_M):
    name, desc = "M10_invalid_access_cancels", "INVALID_ACCESS in RESERVED clears the reservation"
    def mutate(self, c):
        if c.operation == Op.INVALID_ACCESS and self.state == S.RESERVED:
            self._clear(); return Result(False, "invalid_access")

class M11_ExpireKeepsCustomer(_M):
    name, desc = "M11_expire_keeps_customer", "EXPIRE leaves customer_id behind"
    def mutate(self, c):
        if c.operation == Op.EXPIRE and self.state == S.RESERVED and c.expired:
            cust = self.customer_id; self._clear(); self.customer_id = cust
            return Result(True, "expired")

class M12_DepositPrefixOnly(_M):
    name, desc = "M12_deposit_prefix_only", "DEPOSIT accepts any code starting with 'R-' (other customer's code)"
    def mutate(self, c):
        if c.operation == Op.DEPOSIT and self.state == S.RESERVED and c.code.startswith("R-"):
            self.state, self.retrieval_code = S.OCCUPIED, f"P-{self.customer_id}"
            return Result(True, "deposited")

class M13_RejectedReserveMutates(_M):
    name, desc = "M13_rejected_reserve_mutates", "rejected RESERVE in RESERVED overwrites customer_id"
    def mutate(self, c):
        if c.operation == Op.RESERVE and self.state == S.RESERVED:
            self.customer_id = c.customer_id; return Result(False, "locker_not_available")

class M14_EquivalentReserveClears(_M):
    name, desc = "M14_equivalent_reserve_resets_retrieval", "RESERVE also sets retrieval_code=None (already None in AVAILABLE)"
    equivalent = True
    def mutate(self, c):
        r = super(_M, self).execute(c)
        if c.operation == Op.RESERVE and r.accepted:
            self.retrieval_code = None
        return r


MUTANTS = [M01_ReserveWhenOccupied, M02_DepositInMaintenance, M03_RetrieveNoAuth, M04_ExpireIgnoresFlag,
           M05_StaleRetrievalCode, M06_CancelWhenOccupied, M07_BadDepositMutates, M08_DisableWhenReserved,
           M09_EnableWhenAvailable, M10_InvalidAccessCancels, M11_ExpireKeepsCustomer, M12_DepositPrefixOnly,
           M13_RejectedReserveMutates, M14_EquivalentReserveClears]
