# MiniPy Interval Analyzer

An abstract interpreter for **MiniPy**, a subset of Python: one `def`,
integers, booleans, strings, lists, `if`, `while`, and a final `return`.
Programs are parsed, turned into a control flow graph, and analyzed by a
worklist engine that runs on any abstract domain.

The engine and one finished domain, `Sign`, are written for you. The
interval domain is left for you to write. The tests tell you when you are
done.

## Layout

| File | What it is | Edit? |
|---|---|---|
| `interval.py` | the interval domain, with holes | **yes, only this one** |
| `test_interval.py` | the tests | no |
| `domain.py` | the `Domain` interface, the `Sign` domain, and the engine `analyze` | no |
| `syntax.py` | the MiniPy parser and AST | no |
| `cfg.py` | control flow graphs and the `Worklist` | no |
| `examples/` | small MiniPy programs to try | no |

## The holes

Every method of `Interval` that raises `NotImplementedError` is yours. Read
`Sign` in `domain.py` first: it is a finished domain with the same methods.
An interval is `BOT` (empty) or `Itv(lo, hi)` with `lo <= hi`; a bound may be
`-INF` or `INF`. The helper `mk(lo, hi)` gives `BOT` when the bounds cross.

1. **Lattice**: `le`, `join`, `meet`, `alpha`.
2. **Transformers**: `binop` for `+` and `*`, `unop` for `-`.
3. **Refinement**: `refine(op, a, b)`, what `a op b` tells about both sides,
   for `<`, `<=`, `>`, `>=`, `==` and `!=`.
4. **Widening** with thresholds, `widen(a, b)`: a bound that moved jumps to the
   next threshold in `self.thresholds`, or to infinity if there is none.
5. **Narrowing**, `narrow(a, b)`: replace only the infinite bounds.

The docstring of each method says exactly what it must return. Every method
must accept `BOT`. Define any helper you like.

## Running the engine

```python
from syntax import parse
from cfg import build
from domain import analyze, returned, constants
from interval import Interval

g = build(parse(open("examples/bounded.py").read()))
res = analyze(g, Interval())                      # one state per point
print(res[2]["x"])                                # the loop head: [0, inf]
print(analyze(g, Interval(), narrowing=True)[2]["x"])          # [0, 10]
print(analyze(g, Interval(), delay=10)[2]["x"])                # [0, 10]
print(analyze(g, Interval(constants(g)))[2]["x"])              # [0, 10]
```

`analyze(g, dom, widening=True, narrowing=False, delay=0)`:

- `widening`: use `dom.widen` at loop heads. Without it, the analysis of a
  loop may never stop, and the engine raises `RuntimeError`.
- `narrowing`: after widening, go around again with `dom.narrow`.
- `delay`: join this many times at a loop head before widening.

Thresholds belong to the domain: `Interval({0, 10})`. The engine's
`constants(g)` collects the integer literals of a program, the usual choice.

## Running the tests

```
python3 -m unittest test_interval
```

Run one class at a time while you work:

```
python3 -m unittest test_interval.TestLattice
```

The tests include a loop that does not stop without widening: before your
`widen` works, you will see the engine give up.

## Requirements

Python 3.12 or later. No packages beyond the standard library.
