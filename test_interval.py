import unittest

from syntax import parse
from cfg import build, find
from domain import analyze, returned, constants, Sign
from interval import Interval, Itv, INF, BOT, TOP


def run(src, thresholds=(), **kw):
    g = build(parse(src))
    return g, analyze(g, Interval(thresholds), **kw)


def head(g, res):
    return res[next(iter(g.loop_heads))]


class TestLattice(unittest.TestCase):
    def setUp(self):
        self.d = Interval()

    def test_order(self):
        d = self.d
        self.assertTrue(d.le(Itv(1, 2), Itv(0, 3)))
        self.assertFalse(d.le(Itv(0, 3), Itv(1, 2)))
        self.assertTrue(d.le(BOT, Itv(0, 0)))
        self.assertTrue(d.le(Itv(0, 0), TOP))

    def test_join_and_meet(self):
        d = self.d
        self.assertEqual(d.join(Itv(1, 2), Itv(5, 6)), Itv(1, 6))
        self.assertEqual(d.meet(Itv(1, 5), Itv(3, 9)), Itv(3, 5))
        self.assertIs(d.meet(Itv(1, 2), Itv(5, 6)), BOT)

    def test_arithmetic(self):
        d = self.d
        self.assertEqual(d.binop("+", Itv(1, 2), Itv(10, 20)), Itv(11, 22))
        self.assertEqual(d.binop("*", Itv(2, 3), Itv(4, 5)), Itv(8, 15))
        self.assertEqual(d.binop("*", Itv(-2, 3), Itv(-4, 5)), Itv(-12, 15))
        self.assertEqual(d.unop("-", Itv(1, 3)), Itv(-3, -1))
        self.assertEqual(d.unop("-", Itv(-INF, 2)), Itv(-2, INF))

    def test_zero_times_infinity_is_zero(self):
        d = self.d
        self.assertEqual(d.binop("*", Itv(0, 0), Itv(1, INF)), Itv(0, 0))
        self.assertEqual(d.binop("*", Itv(0, 0), TOP), Itv(0, 0))
        self.assertEqual(d.binop("*", Itv(0, 2), Itv(3, INF)), Itv(0, INF))
        self.assertEqual(d.binop("*", Itv(-1, 1), Itv(2, INF)), TOP)

    def test_comparisons_and_not_are_not_numbers(self):
        d = self.d
        self.assertEqual(d.binop("<", Itv(0, 1), Itv(2, 3)), TOP)
        self.assertEqual(d.binop("==", Itv(0, 0), Itv(0, 0)), TOP)
        self.assertEqual(d.unop("not", Itv(0, 1)), TOP)

    def test_bottom_in_transformers(self):
        d = self.d
        self.assertIs(d.binop("+", BOT, Itv(0, 0)), BOT)
        self.assertIs(d.binop("*", Itv(0, 0), BOT), BOT)
        self.assertIs(d.unop("-", BOT), BOT)

    def test_alpha_and_gamma(self):
        d = self.d
        self.assertEqual(d.alpha({3, -1, 7}), Itv(-1, 7))
        self.assertIs(d.alpha(set()), BOT)
        self.assertEqual(d.gamma(BOT), "{}")


class TestWidening(unittest.TestCase):
    def setUp(self):
        self.d = Interval()

    def test_widen_jumps_to_infinity(self):
        d = self.d
        self.assertEqual(d.widen(Itv(0, 0), Itv(0, 1)), Itv(0, INF))
        self.assertEqual(d.widen(Itv(0, 0), Itv(-1, 0)), Itv(-INF, 0))
        self.assertEqual(d.widen(Itv(0, 5), Itv(0, 5)), Itv(0, 5))

    def test_widen_is_an_upper_bound(self):
        d = self.d
        for a, b in [(Itv(0, 0), Itv(0, 1)), (Itv(2, 3), Itv(1, 9)),
                     (BOT, Itv(0, 0))]:
            self.assertTrue(d.le(d.join(a, b), d.widen(a, b)))

    def test_narrow_only_refines_infinite_bounds(self):
        d = self.d
        self.assertEqual(d.narrow(Itv(0, INF), Itv(0, 10)), Itv(0, 10))
        self.assertEqual(d.narrow(Itv(0, 5), Itv(0, 3)), Itv(0, 5))
        self.assertEqual(d.narrow(Itv(-INF, 5), Itv(-3, 4)), Itv(-3, 5))
        self.assertEqual(d.narrow(TOP, Itv(1, 2)), Itv(1, 2))

    def test_narrow_with_bottom(self):
        d = self.d
        self.assertIs(d.narrow(Itv(0, INF), BOT), BOT)
        self.assertIs(d.narrow(BOT, Itv(0, 1)), BOT)

    def test_a_bound_that_shrinks_does_not_jump(self):
        d = self.d
        self.assertEqual(d.widen(Itv(0, 5), Itv(2, 3)), Itv(0, 5))
        self.assertEqual(d.widen(Itv(0, 5), Itv(1, 9)), Itv(0, INF))

    def test_without_widening_the_analysis_does_not_terminate(self):
        g = build(parse("def f(n):\n    i = 0\n    while i < n:\n"
                        "        i = i + 1\n    return i\n"))
        # NotImplementedError is a RuntimeError too: check it is the engine
        with self.assertRaisesRegex(RuntimeError, "no fixpoint"):
            analyze(g, Interval(), widening=False, limit=400)

    def test_with_widening_it_does(self):
        g, res = run("def f(n):\n    i = 0\n    while i < n:\n"
                     "        i = i + 1\n    return i\n")
        self.assertEqual(head(g, res)["i"], Itv(0, INF))


class TestPrecision(unittest.TestCase):
    LOOP = ("def f():\n    i = 0\n    while i < 10:\n"
            "        i = i + 1\n    return i\n")

    def test_narrowing_recovers_the_bound(self):
        g, res = run(self.LOOP, narrowing=True)
        self.assertEqual(head(g, res)["i"], Itv(0, 10))
        self.assertEqual(returned(g, Interval(), res), Itv(10, 10))

    def test_a_falling_bound_goes_down_and_comes_back(self):
        src = ("def f():\n    x = 10\n    while 0 < x:\n"
               "        x = x + -3\n    return x\n")
        g, res = run(src)
        self.assertEqual(head(g, res)["x"], Itv(-INF, 10))
        g, res = run(src, narrowing=True)
        self.assertEqual(head(g, res)["x"], Itv(-2, 10))
        self.assertEqual(returned(g, Interval(), res), Itv(-2, 0))

    def test_widening_alone_loses_it(self):
        g, res = run(self.LOOP)                 # narrowing is off by default
        self.assertEqual(returned(g, Interval(), res), Itv(10, INF))

    def test_condition_refines_both_sides(self):
        g, res = run("def f(a, b):\n    if a < b:\n        a = a + 0\n    return a\n")
        t = find(g, "assume(a < b)").dst
        self.assertEqual(res[t]["a"], Itv(-INF, INF))    # b is unbounded above

    def test_a_bounded_parameter_stays_bounded(self):
        g, res = run("def f(n):\n    if n <= 100:\n        n = n\n"
                     "    else:\n        n = 100\n    return n\n")
        self.assertEqual(returned(g, Interval(), res), Itv(-INF, 100))

    def test_intervals_are_non_relational(self):
        """i == j is invisible: each variable is bounded on its own."""
        g, res = run("def f(n):\n    i = 0\n    j = 0\n    while i < n:\n"
                     "        i = i + 1\n        j = j + 1\n    return j\n")
        h = head(g, res)
        self.assertEqual(h["i"], Itv(0, INF))
        self.assertEqual(h["j"], Itv(0, INF))


class TestRefine(unittest.TestCase):
    def setUp(self):
        self.d = Interval()

    def test_less_than(self):
        self.assertEqual(self.d.refine("<", Itv(5, 9), Itv(0, 7)), (Itv(5, 6), Itv(6, 7)))

    def test_less_or_equal(self):
        self.assertEqual(self.d.refine("<=", Itv(5, 9), Itv(0, 7)), (Itv(5, 7), Itv(5, 7)))

    def test_greater_than(self):
        self.assertEqual(self.d.refine(">", Itv(0, 9), Itv(5, 7)), (Itv(6, 9), Itv(5, 7)))
        self.assertEqual(self.d.refine(">", Itv(0, 6), Itv(5, 9)), (Itv(6, 6), Itv(5, 5)))

    def test_greater_or_equal(self):
        self.assertEqual(self.d.refine(">=", Itv(0, 6), Itv(5, 9)), (Itv(5, 6), Itv(5, 6)))

    def test_equal(self):
        self.assertEqual(self.d.refine("==", Itv(0, 5), Itv(3, 9)), (Itv(3, 5), Itv(3, 5)))

    def test_impossible(self):
        self.assertEqual(self.d.refine("<", Itv(5, 9), Itv(0, 5)), (BOT, BOT))
        self.assertEqual(self.d.refine("==", Itv(0, 1), Itv(2, 3)), (BOT, BOT))

    def test_infinite_bounds(self):
        self.assertEqual(self.d.refine("<", TOP, Itv(0, 10)), (Itv(-INF, 9), Itv(0, 10)))
        self.assertEqual(self.d.refine("<", Itv(0, INF), TOP), (Itv(0, INF), Itv(1, INF)))

    def test_bottom(self):
        self.assertEqual(self.d.refine("<", BOT, Itv(0, 1)), (BOT, BOT))
        self.assertEqual(self.d.refine("!=", Itv(0, 1), BOT), (BOT, BOT))


class TestThresholds(unittest.TestCase):
    LOOP = ("def f():\n    i = 0\n    while i < 10:\n"
            "        i = i + 1\n    return i\n")

    def test_jump_to_the_next_threshold(self):
        d = Interval({0, 5, 10})
        self.assertEqual(d.widen(Itv(0, 0), Itv(0, 1)), Itv(0, 5))
        self.assertEqual(d.widen(Itv(0, 5), Itv(0, 6)), Itv(0, 10))
        self.assertEqual(d.widen(Itv(0, 10), Itv(0, 11)), Itv(0, INF))

    def test_a_threshold_equal_to_the_new_bound(self):
        d = Interval({7, -3})
        self.assertEqual(d.widen(Itv(0, 3), Itv(0, 7)), Itv(0, 7))
        self.assertEqual(d.widen(Itv(0, 3), Itv(-3, 3)), Itv(-3, 3))

    def test_the_threshold_is_past_the_new_bound(self):
        d = Interval({5, 10, -5, -10})
        self.assertEqual(d.widen(Itv(0, 0), Itv(0, 7)), Itv(0, 10))
        self.assertEqual(d.widen(Itv(0, 0), Itv(-7, 0)), Itv(-10, 0))

    def test_down_as_well_as_up(self):
        d = Interval({-10, -3, 4})
        self.assertEqual(d.widen(Itv(0, 0), Itv(-1, 1)), Itv(-3, 4))
        self.assertEqual(d.widen(Itv(-3, 4), Itv(-4, 4)), Itv(-10, 4))
        self.assertEqual(d.widen(Itv(-10, 4), Itv(-11, 4)), Itv(-INF, 4))

    def test_only_moving_bounds_jump(self):
        d = Interval({0, 100})
        self.assertEqual(d.widen(Itv(0, 5), Itv(2, 3)), Itv(0, 5))
        self.assertEqual(d.widen(Itv(1, 5), Itv(1, 9)), Itv(1, 100))

    def test_bottom(self):
        d = Interval({3})
        self.assertEqual(d.widen(BOT, Itv(0, 1)), Itv(0, 1))
        self.assertEqual(d.widen(Itv(0, 1), BOT), Itv(0, 1))

    def test_the_right_constant_makes_narrowing_unnecessary(self):
        g, res = run(self.LOOP, thresholds={0, 10}, narrowing=False)
        self.assertEqual(head(g, res)["i"], Itv(0, 10))
        self.assertEqual(returned(g, Interval(), res), Itv(10, 10))

    def test_a_useless_constant_costs_a_lap(self):
        g, res = run(self.LOOP, thresholds={0, 5, 10}, narrowing=False)
        self.assertEqual(head(g, res)["i"], Itv(0, 10))

    def test_not_equal_needs_a_threshold(self):
        src = ("def f():\n    i = 0\n    while i != 4:\n"
               "        i = i + 1\n    return i\n")
        g, res = run(src)                       # narrowing cannot help
        self.assertEqual(head(g, res)["i"], Itv(0, INF))
        g, res = run(src, thresholds={4})
        self.assertEqual(head(g, res)["i"], Itv(0, 4))
        self.assertEqual(res[find(g, "assume(i != 4)").dst]["i"], Itv(0, 3))

    def test_constants_of_a_program(self):
        g = build(parse("def f(x):\n    y = [7, -2]\n    while x < 10:\n"
                        "        x = x + -3\n    return x * 2\n"))
        self.assertEqual(constants(g), {7, -2, 10, -3, 2})


class TestDelay(unittest.TestCase):
    LOOP = TestThresholds.LOOP

    def test_no_delay_is_plain_widening(self):
        g, res = run(self.LOOP, narrowing=False, delay=0)
        self.assertEqual(head(g, res)["i"], Itv(0, INF))

    def test_a_short_delay_does_not_help_a_long_loop(self):
        g, res = run(self.LOOP, narrowing=False, delay=3)
        self.assertEqual(head(g, res)["i"], Itv(0, INF))

    def test_a_long_enough_delay_is_exact(self):
        g, res = run(self.LOOP, narrowing=False, delay=10)
        self.assertEqual(head(g, res)["i"], Itv(0, 10))
        self.assertEqual(returned(g, Interval(), res), Itv(10, 10))

    def test_a_short_loop_is_exact_with_a_small_delay(self):
        g, res = run("def f():\n    i = 0\n    while i < 2:\n"
                     "        i = i + 1\n    return i\n", narrowing=False, delay=2)
        self.assertEqual(head(g, res)["i"], Itv(0, 2))

    def test_delay_still_terminates_on_an_unbounded_loop(self):
        g, res = run("def f(n):\n    i = 0\n    while i < n:\n"
                     "        i = i + 1\n    return i\n", delay=5)
        self.assertEqual(head(g, res)["i"], Itv(0, INF))


class TestNotEqual(unittest.TestCase):
    def setUp(self):
        self.d = Interval()

    def test_cuts_an_end(self):
        d = self.d
        self.assertEqual(d.refine("!=", Itv(0, 4), Itv(4, 4)), (Itv(0, 3), Itv(4, 4)))
        self.assertEqual(d.refine("!=", Itv(4, 9), Itv(4, 4)), (Itv(5, 9), Itv(4, 4)))
        self.assertEqual(d.refine("!=", Itv(4, 4), Itv(0, 9)), (Itv(4, 4), Itv(0, 9)))

    def test_not_the_middle(self):
        self.assertEqual(self.d.refine("!=", Itv(0, 9), Itv(4, 4)), (Itv(0, 9), Itv(4, 4)))

    def test_nothing_left(self):
        self.assertEqual(self.d.refine("!=", Itv(3, 3), Itv(3, 3)), (BOT, BOT))

    def test_not_a_single_value(self):
        self.assertEqual(self.d.refine("!=", Itv(0, 4), Itv(4, 5)), (Itv(0, 4), Itv(4, 5)))


class TestSign(unittest.TestCase):
    def test_sign_domain(self):
        g = build(parse("def f():\n    x = 1\n    y = 0\n    z = x + y\n"
                        "    return z\n"))
        self.assertEqual(returned(g, Sign(), analyze(g, Sign())), "+")

    def test_sign_join_loses_information(self):
        g = build(parse("def f(c):\n    x = 1\n    if c < 0:\n        x = -1\n"
                        "    return x\n"))
        self.assertEqual(returned(g, Sign(), analyze(g, Sign())), "-+")

    def test_the_same_engine_runs_both_domains(self):
        g = build(parse("def f(n):\n    i = 0\n    while i < n:\n"
                        "        i = i + 1\n    return i\n"))
        for dom in (Sign(), Interval()):
            with self.subTest(domain=type(dom).__name__):
                self.assertEqual(set(analyze(g, dom)), set(g.nodes))


if __name__ == "__main__":
    unittest.main()
