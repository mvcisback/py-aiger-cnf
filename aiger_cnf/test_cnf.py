from hypothesis import given
from aiger import hypothesis as aigh


from aiger_cnf import aig2cnf


@given(aigh.Circuits)
def test_smoke_aig2cnf(circ):
    aig2cnf(circ.unroll(1))
