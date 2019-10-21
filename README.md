# py-aiger-cnf
Python library to convert between AIGER and CNF

[![Build Status](https://cloud.drone.io/api/badges/mvcisback/py-aiger-cnf/status.svg)](https://cloud.drone.io/mvcisback/py-aiger-cnf)
[![codecov](https://codecov.io/gh/mvcisback/py-aiger-cnf/branch/master/graph/badge.svg)](https://codecov.io/gh/mvcisback/py-aiger-cnf)
[![PyPI version](https://badge.fury.io/py/py-aiger-cnf.svg)](https://badge.fury.io/py/py-aiger-cnf)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-generate-toc again -->
**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)

<!-- markdown-toc end -->

# Installation

If you just need to use `aiger_cnf`, you can just run:

`$ pip install py-aiger-cnf`

For developers, note that this project uses the
[poetry](https://poetry.eustace.io/) python package/dependency
management tool. Please familarize yourself with it and then
run:

`$ poetry install`

# Usage

The primary entry point for using `aiger_cnf` is the `aig2cnf`
function which, unsurprisingly, maps `AIG` objects to `CNF` objects.

```python
import aiger
from aiger_cnf import aig2cnf

x, y, z = map(aiger.atom, ('x', 'y', 'z'))
expr = (x & y) | ~z
cnf = aig2cnf(expr.aig)
```

Note that this library also supports `aiger` wrapper libraries so long
as they export a `.aig` attribute. Thus, could also
write:

```python
cnf = aig2cnf(expr)
```


The `CNF` object is a `NamedTuple` with the following three fields:

1. `clauses`: A list of tuples of ints, e.g., `[(1,2,3), (-1,
   2)]`. Each integer represents a variable's id, with the sign
   indicating the polarity of the variable.
2. `symbol_table`: A
   [bidict](https://bidict.readthedocs.io/en/master/) from strings to
   variable ids.
3. `max_var`: The maximum (in absolute value) index present in
   `clauses`.
