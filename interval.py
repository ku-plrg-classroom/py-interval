"""The interval domain, with widening (and thresholds) and narrowing."""

from __future__ import annotations

from dataclasses import dataclass

from domain import Domain

INF = float("inf")


@dataclass(frozen=True)
class Itv:
    lo: float          # int or -INF
    hi: float          # int or +INF

    def __str__(self) -> str:
        f = lambda v: "-inf" if v == -INF else "inf" if v == INF else str(int(v))
        return f"[{f(self.lo)}, {f(self.hi)}]"


BOT = None             # the empty interval
TOP = Itv(-INF, INF)


def mk(lo: float, hi: float) -> Itv | None:
    """[lo, hi], or BOT if it is empty."""
    return Itv(lo, hi) if lo <= hi else BOT


class Interval(Domain):
    """An element is BOT, or Itv(lo, hi) with lo <= hi: the integers n with
    lo <= n <= hi. A bound may be infinite. Every method must accept BOT."""

    bot, top = BOT, TOP

    def __init__(self, thresholds=()):
        self.thresholds = sorted(set(thresholds))      # T, for widening

    # -- lattice -----------------------------------------------------------

    def le(self, a, b):
        """a is included in b. BOT is included in everything."""
        raise NotImplementedError("TODO: le")

    def join(self, a, b):
        """The smallest interval containing both."""
        raise NotImplementedError("TODO: join")

    def meet(self, a, b):
        """The intersection, or BOT if it is empty."""
        raise NotImplementedError("TODO: meet")

    def alpha(self, ns):
        """The smallest interval containing the set of integers ns (BOT if
        ns is empty)."""
        raise NotImplementedError("TODO: alpha")

    def gamma(self, a):
        if a is BOT:
            return "{}"
        lo = "" if a.lo == -INF else f"{int(a.lo)} <= "
        hi = "" if a.hi == INF else f" <= {int(a.hi)}"
        return "Z" if not lo and not hi else f"{{n | {lo}n{hi}}}"

    def of_num(self, n):
        return Itv(n, n)

    # -- transformers ------------------------------------------------------

    def binop(self, op, a, b):
        """The interval of `x op y` for x in a and y in b.

        op is "+" or "*". For "*", 0 times an infinite bound counts as 0.
        Any other op (a comparison) does not give a number: return TOP.
        If a or b is BOT, the result is BOT.
        """
        raise NotImplementedError("TODO: binop")

    def unop(self, op, a):
        """op is "-" (negation); any other op (`not`) gives TOP.
        BOT stays BOT."""
        raise NotImplementedError("TODO: unop")

    # -- widening and narrowing --------------------------------------------

    def widen(self, a, b):
        """a is the old value at a loop head, b the new one.

        A bound of b that moved past the bound of a jumps: a lower bound to
        the greatest threshold t <= b.lo, an upper bound to the smallest
        threshold t >= b.hi, or to -INF / INF if there is no such threshold.
        A bound that did not move stays as it is in a.
        With no thresholds, every moving bound goes to infinity.
        If a is BOT, the result is b; if b is BOT, it is a.
        """
        raise NotImplementedError("TODO: widen")

    def narrow(self, a, b):
        """a is the value after widening, b a new, smaller one.

        Only the infinite bounds of a are replaced, by those of b; finite
        bounds stay. The result is BOT if either one is BOT, or if it is empty.
        """
        raise NotImplementedError("TODO: narrow")

    # -- refinement by conditions ------------------------------------------

    def refine(self, op, a, b):
        """Assume `x op y` holds, for x in a and y in b. Return the pair
        (a', b'): the values of x and y that can make it true.

        op is "<", "<=", ">", ">=", "==" or "!=".
        For "!=": an interval cannot have a hole, so a value is removed only
        when the other side is a single value at an end, as in
        refine("!=", [0, 4], [4, 4]) == ([0, 3], [4, 4]).
        If either one is BOT, both are BOT. Any other op: (a, b) unchanged.
        """
        raise NotImplementedError("TODO: refine")
