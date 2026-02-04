# pytest-cocotb

A pytest plugin that integrates [cocotb](https://www.cocotb.org/) HDL simulation into pytest, with support for HPC job schedulers.

## Features

- **pytest integration** — run cocotb testbenches as regular pytest tests
- **HPC support** — submit simulation jobs to SGE, SLURM, or local schedulers via [hpc-runner](https://pypi.org/project/hpc-runner/)
- **NFS-safe coordination** — `mkdir`-based locking for reliable build-once semantics across NFS-mounted xdist workers
- **CLI options** — `--simulator`, `--hdl-toplevel`, `--sources`, `--waves`, `--clean`, and more

## Installation

```bash
pip install pytest-cocotb
```

## Quick start

```python
# test_my_design.py
def test_counter(test_session):
    test_session.run(test_module="cocotb_counter")
```

```bash
pytest test_my_design.py --simulator verilator --hdl-toplevel counter --sources rtl/counter.sv
```

The plugin compiles the HDL once per session, then runs each test in an isolated directory. The cocotb test module (`cocotb_counter.py`) contains `@cocotb.test()` coroutines and is **not** collected by pytest directly.

## License

MIT
