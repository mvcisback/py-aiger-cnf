from collections import defaultdict
from typing import NamedTuple, Tuple, List, Mapping, Union

import attr
import aiger
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


Clause = Union[Tuple[int], Tuple[int, int], Tuple[int, int, int]]
Clauses = List[Clause]


class CNF(NamedTuple):
    clauses: Clauses
    input2lit: Mapping[str, int]
    output2lit: Mapping[str, int]
    comments: Tuple[str]


@attr.s(auto_attribs=True, frozen=True)
class LitWrapper:
    gate: Node
    gate2lit: Mapping[Node, int]
    clauses: Clauses

    @property
    def lit(self) -> int:
        return self.gate2lit[self.gate]

    def evolve(self, gate):
        return attr.evolve(self, gate=gate)

    def __and__(self, other):
        wrapped = self.evolve(AndGate(self.gate, other.gate))

        if wrapped.gate not in wrapped.gate2lit:  # Avoid redundant clauses.
            out, left, right = wrapped.lit, self.lit, other.lit
            self.clauses.append((-left, -right, out))  # (left /\ right) -> out
            self.clauses.append((-out, left))          # out -> left
            self.clauses.append((-out, right))         # out -> right

        return wrapped

    def __invert__(self):
        gate = Inverter(self.gate)
        self.gate2lit[gate] = -self.lit
        return self.evolve(gate)


def aig2cnf(circ, *, outputs=None, fresh=None, force_true=True) -> CNF:
    """Convert an AIGER circuit to CNF via the Tseitin transformation."""
    if fresh is None:
        max_var = 0

        def fresh(_):
            nonlocal max_var
            max_var += 1
            return max_var

    circ = aiger.to_aig(circ, allow_lazy=True)
    assert len(circ.latches) == 0

    # Interpret circuit over Lit Boolean Algebra.
    clauses, gate2lit = [], SymbolTable(fresh)

    def lift(obj) -> LitWrapper:
        assert isinstance(obj, (Input, bool))
        if isinstance(obj, bool):
            assert not obj
            obj = ConstFalse()

        gate2lit[obj]  # defaultdict. force add literal for obj.
        return LitWrapper(gate=obj, gate2lit=gate2lit, clauses=clauses)

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
