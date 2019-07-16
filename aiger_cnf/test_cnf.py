from hypothesis import given
from aiger import hypothesis as aigh


from aiger_cnf import aig2cnf


@given(aigh.Circuits)
def smoke_test_aig2cnf():
    aig2cnf(aigh.Circuits)
