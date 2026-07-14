# Manual Usage

This document describes how to run each pipeline phase individually.

## Dataset Matching
Match datasets between two parties using the `match.py` wrapper. For example, using PSI:
```bash
# Bob (server)
python3 scripts/match.py --input path/to/bob.csv --output path/to/bob_out.csv --address 0.0.0.0:10010 psi
# Alice (client)
python3 scripts/match.py --input path/to/alice.csv --output path/to/alice_out.csv --address 127.0.0.1:10010 psi
```
The input must be a CSV file with identifiers in the first column. The output is a CSV containing the matched data ready for the next step.

Supported protocols: `psi`, `cpsi`, `ps3i`, `ps3i-xor`, `pid`. For protocol-specific output formats, example commands, and extra flags, see [matching.md](matching.md).


## Downstream MPC

### Preparing input
Prepare each party's matched output for MP-SPDZ using `iprep.py`:
```bash
python3 scripts/iprep.py --input path/to/alice_out.csv --party 0 --columns 0,1
python3 scripts/iprep.py --input path/to/bob_out.csv --party 1 --columns 0,1
```
Use `--columns` to select which columns (zero-indexed, after the ID column is stripped by `match.py`) to pass to the MPC program. Use `--split --split-ratio 0.8` to produce a train/test split (useful for `linreg`).

### Compiling a program
Compile the desired MPC program with the appropriate options:
```bash
./scripts/compile.sh xtabs.py -R 64 -Z 2 -b 100000 --rows 5000 --protocol psi --aggregation sum --group_by a --values b --n_cat_1 4
./scripts/compile.sh linreg.py -R 64 -Z 2 --rows 5000 --protocol psi --features a3b1 --label b
```
The `--protocol` flag must match the one used in the matching step so the program knows how to handle the input format. Use `--help` for a full list of options per program.

### Running
Run all parties at once on localhost:
```bash
./scripts/run.sh ring.sh <program_name>
```
Or run each party in a separate terminal:
```bash
./scripts/run.sh replicated-ring-party.x 0 <program_name>
./scripts/run.sh replicated-ring-party.x 1 <program_name>
./scripts/run.sh replicated-ring-party.x 2 <program_name>
```
`run.sh` is a thin wrapper that changes into the `MP-SPDZ/` directory and forwards all arguments. 
> Any MP-SPDZ protocol script or binary should work in place of `ring.sh` or `replicated-ring-party.x`, respectively. Refer to the [MP-SPDZ documentation](https://mp-spdz.readthedocs.io) for the full list.

#### As-server mode
When compiled with `--as-server`, the MPC parties wait for live data over socket connections instead of reading from files.
```bash
# Start the MPC parties in localhost
./scripts/run.sh ring.sh <program_name>

# In separate terminals, send inputs from each party (in localhost as well)
./scripts/run.sh client-input.x --client_id 0 --nparties 3
./scripts/run.sh client-input.x --client_id 1 --nparties 3 --finish
```
The last client to connect must pass `--finish` to signal the start of computation. By default `client-input.x` connects to `localhost`. You can pass `--host <host_1>,...,<host_n>` to connect to hosts outside of localhost.
