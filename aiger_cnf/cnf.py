from collections import defaultdict
from typing import NamedTuple, Tuple, List, Mapping, Optional

import funcy as fn
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
    symbol_table: Mapping[str, int]
    max_var: Optional[int] = None


def aig2cnf(circ, output=None, symbol_table=None, max_var=0,
            *, fresh=None, force_true=True):
    """Convert an AIGER circuit to CNF via the Tseitin transformation."""
    circ = aiger.to_aig(circ)

    assert len(circ.latches) == 0
    if output is None:
        assert len(circ.outputs) == 1
        output = fn.first(circ.outputs)

    if fresh is None:
        def fresh(_):
            nonlocal max_var
            max_var += 1
            return max_var
    else:
        max_var = None

    output = dict(circ.node_map)[output]
    # maps input names to tseitin variables
    if symbol_table is None:
        symbol_table = {}

    symbol_table = SymbolTable(fresh, symbol_table)

    clauses, gates = [], {}  # maps gates to tseitin variables
    for gate in cmn.eval_order(circ):
        if isinstance(gate, aiger.aig.ConstFalse):
            true_var = symbol_table[gate]
            clauses.append((true_var,))
            gates[gate] = -true_var
        elif isinstance(gate, aiger.aig.Inverter):
            gates[gate] = -gates[gate.input]
        elif isinstance(gate, aiger.aig.Input):
            gates[gate] = symbol_table[gate.name]
        elif isinstance(gate, aiger.aig.AndGate):
            gates[gate] = fresh(gate)
            clauses.append((-gates[gate.left], -gates[gate.right],  gates[gate]))  # noqa
            clauses.append((gates[gate.left],                     -gates[gate]))  # noqa
            clauses.append((                    gates[gate.right], -gates[gate]))  # noqa

    if force_true:
        clauses.append((gates[output],))

    return CNF(clauses, bidict(symbol_table), max_var)
