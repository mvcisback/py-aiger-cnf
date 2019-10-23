import aiger
import hypothesis.strategies as st
from aiger import hypothesis as aigh
from hypothesis import given
from pysat.solvers import Glucose3

from aiger_cnf import aig2cnf


@given(aigh.Circuits, st.data())
def test_aig2cnf(circ, data):
    expr1 = aiger.BoolExpr(circ.unroll(1))
    cnf = aig2cnf(expr1)
    g = Glucose3()
    for c in cnf.clauses:
        g.add_clause(c)

    test_input = {i: data.draw(st.booleans()) for i in expr1.inputs}
    assumptions = []
    for name, val in test_input.items():
        if name not in cnf.symbol_table:
            continue
        sym = cnf.symbol_table[name]
        if not val:
            sym *= -1
        assumptions.append(sym)

    assert expr1(test_input) == g.solve(assumptions=assumptions)


def test_fresh():
    expr = aiger.atom('x') | aiger.atom('y')
    count = -1

    def fresh(_):
        nonlocal count
        count -= 1
        return count

    cnf = aig2cnf(expr, fresh=fresh)
    assert cnf.max_var is None
    assert all(x < 1 for x in cnf.symbol_table.values())


def test_force_true():
    expr = aiger.atom('x') | aiger.atom('y')

    cnf1 = aig2cnf(expr, force_true=True)
    cnf2 = aig2cnf(expr, force_true=False)
    assert set(cnf1.clauses) > set(cnf2.clauses)
    assert len(cnf1.clauses) == len(cnf2.clauses) + 1
