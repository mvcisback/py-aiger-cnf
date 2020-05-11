from collections import defaultdict
from typing import NamedTuple, Tuple, List, Mapping, Hashable

import attr
import aiger
import funcy as fn
from aiger.aig import Node, Inverter, ConstFalse, AndGate, Input
from bidict import bidict


class SymbolTable(defaultdict):
    def __init__(self, func, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.func = func

    def __missing__(self, key: Node):
        if isinstance(key, ConstFalse):
            self[key] = -self[Inverter(key)]
        else:
            self[key] = self.func(key)
        return self[key]


class CNF(NamedTuple):
    clauses: List[Tuple[int]]
    input2lit: Mapping[str, int]
    output2lit: Mapping[str, int]
    comments: Tuple[str]


def aig2cnf(circ, *, outputs=None, fresh=None, force_true=True):
    """Convert an AIGER circuit to CNF via the Tseitin transformation."""
    if fresh is None:
        max_var = 0

        def fresh(_):
            nonlocal max_var
            max_var += 1
            return max_var

    circ = aiger.to_aig(circ, allow_lazy=True)
    assert len(circ.latches) == 0

    # Define Boolean Algebra over clauses.
    clauses, gate2lit = [], SymbolTable(fresh)

    @attr.s(auto_attribs=True, frozen=True)
    class LitWrapper:
        lit: Hashable
        gate: Node

        @fn.memoize
        def __and__(self, other):
            gate = AndGate(self.gate, other.gate)
            wrapped = LitWrapper(gate2lit[gate], gate)

            out, left, right = wrapped.lit, self.lit, other.lit
            clauses.append((-left, -right, out))     # (left /\ right) -> out
            clauses.append((-out, left))             # out -> left
            clauses.append((-out, right))            # out -> right
            return wrapped

        def __invert__(self):
            gate = Inverter(self.gate)
            gate2lit[gate] = -self.lit
            return LitWrapper(gate2lit[gate], gate)

    def lift(obj) -> LitWrapper:
        assert isinstance(obj, (Input, bool))
        if isinstance(obj, bool):
            assert not obj
            obj = ConstFalse()

        return LitWrapper(gate2lit[obj], obj)

    # Interpret circ over Lit Boolean Algebra.
    inputs = {i: aiger.aig.Input(i) for i in circ.inputs}
    out2lit, _ = circ(inputs=inputs, lift=lift)
    out2lit = {k: v.lit for k, v in out2lit.items()}  # Remove Lit wrapper.
    in2lit = bidict({i: gate2lit[aiger.aig.Input(i)] for i in circ.inputs})

    # Force True/False variable to be true/false.
    if ConstFalse() in gate2lit:
        clauses.append((-gate2lit[ConstFalse()],))

    # Force outputs to appear as positive variables.
    for name, gate in circ.node_map.items():
        if not isinstance(gate, aiger.aig.Inverter):
            continue

        oldv = out2lit[name] = fresh(gate)
        newv = gate2lit[gate]
        clauses.append((-newv,  oldv))
        clauses.append((newv,  -oldv))

    if force_true:
        if outputs is None:
            outputs = circ.outputs

        for name in outputs:
            clauses.append((out2lit[name],))

    return CNF(clauses, in2lit, out2lit, circ.comments)
