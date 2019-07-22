from collections import defaultdict
from typing import NamedTuple, Tuple, List, Mapping

import funcy as fn
from bidict import bidict

import aiger
import aiger.common as cmn


class CNF(NamedTuple):
    clauses: List[Tuple[int]]
    symbol_table: Mapping[str, int]
    max_var: int

    def id2name(self, idx):
        return self.symbol_table.inv[abs(idx)]

    def name2id(self, name):
        return self.symbol_table[name]


def aig2cnf(circ, output=None):
    """Convert an AIGER circuit to CNF via the Tseitin transformation."""
    circ = circ.aig  # Extract AIG from potential wrapper.
    assert len(circ.latches) == 0
    if output is None:
        assert len(circ.outputs) == 1
        output = fn.first(circ.outputs)

    max_var = 0

    def fresh():
        nonlocal max_var
        max_var += 1
        return max_var

    output = dict(circ.node_map)[output]
    symbol_table = defaultdict(fresh)  # maps input names to tseitin variables

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
            gates[gate] = fresh()
            clauses.append((-gates[gate.left], -gates[gate.right],  gates[gate]))  # noqa
            clauses.append((gates[gate.left],                     -gates[gate]))  # noqa
            clauses.append((                    gates[gate.right], -gates[gate]))  # noqa

    clauses.append((gates[output],))
    return CNF(clauses, bidict(symbol_table), max_var)
