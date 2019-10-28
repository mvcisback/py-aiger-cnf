from collections import defaultdict
from typing import NamedTuple, Tuple, List, Mapping

from bidict import bidict

import aiger
import aiger.common as cmn


class SymbolTable(defaultdict):
    def __init__(self, func, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.func = func

    def __missing__(self, key):
        self[key] = val = self.func(key)
        return val


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

    circ = aiger.to_aig(circ)
    assert len(circ.latches) == 0

    clauses, seen_false, gate2lit = [], False, SymbolTable(fresh)
    for gate in cmn.eval_order(circ):
        if isinstance(gate, aiger.aig.ConstFalse) and not seen_false:
            seen_false = True
            true_var = fresh(True)
            gate2lit[gate] = -true_var
            clauses.append((true_var,))

        elif isinstance(gate, aiger.aig.Inverter):
            gate2lit[gate] = -gate2lit[gate.input]

        elif isinstance(gate, aiger.aig.AndGate):
            clauses.append((-gate2lit[gate.left], -gate2lit[gate.right],  gate2lit[gate]))  # noqa
            clauses.append((gate2lit[gate.left],                         -gate2lit[gate]))  # noqa
            clauses.append((                       gate2lit[gate.right], -gate2lit[gate]))  # noqa

    in2lit = bidict({i: gate2lit[aiger.aig.Input(i)] for i in circ.inputs})

    out2lit = bidict()
    for name, gate in circ.node_map.items():
        if not isinstance(gate, aiger.aig.Inverter):
            out2lit[name] = gate2lit[gate]
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
