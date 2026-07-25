# Split MPC Pipeline
This repository contains a practical implementation of a privacy-preserving pipeline using multi-party computation. It focuses on secure dataset matching and subsequent downstream statistical analysis.

The pipeline includes support for protocols such as PSI and Circuit-PSI to privately match datasets between parties as well as MPC programs for use with the MP-SPDZ framework.

## Environment Setup
Initialize the submodules first:
```bash
git submodule update --init --recursive
```

### Native
Build whichever matching protocols you need:
```bash
bash scripts/build_submodules.sh
```
> Modules are independent. You can build only the ones you need. Use the `-h` flag for more info.

Install MP-SPDZ:
```bash
bash scripts/install.sh
```
This downloads the pre-built release binaries. To build from source instead, pass `yes` as an argument (this may take a long time).

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Before running any MPC computation, you may need to generate SSL certificates:
```bash
cd MP-SPDZ
Scripts/setup-ssl.sh <n_parties>        # party-to-party certs (required for all runs)
Scripts/setup-clients.sh <n_parties>    # client certs (required for as-server mode only)
```

### Docker
Build the runtime image from the project root. Submodules must be initialized before building if you want matching protocol support:
```bash
docker build --target runtime -t split-mpc .
# To include only specific matching protocols:
docker build --target runtime --build-arg modules=volepsi -t split-mpc .
```
SSL certificates and MP-SPDZ are set up automatically during the image build.

Run the pipeline inside the container by mounting your data and working interactively:
```bash
docker run --rm -it -v $(pwd)/data:/workspace/data split-mpc bash
```

## Usage
To generate sample data for experimenting with the pipeline, use `scripts/geninput.py`.

The recommended way to run the full pipeline is via `pipeline.sh`, which runs all phases from a single config file. Example configs are provided in `config/examples/`. For manual step-by-step usage, see [docs/usage.md](docs/usage.md).

Each party runs:
```bash
bash scripts/pipeline.sh <config_file> [KEY=value ...]
```
The config file is a shell script that sets the variables consumed by each phase. Any variable can be overridden inline. Individual phases can be skipped by setting `RUN_MATCH`, `RUN_IPREP`, `RUN_COMPILE`, or `RUN_MPC` to `false` in the config.

#### Direct computation
All phases run on the data owners' machines. Each party runs the full pipeline sequentially, with matching, input preparation, compilation, and running the MPC program.
```bash
# Alice (terminal 1)
bash scripts/pipeline.sh config/examples/direct/alice.sh
# Bob (terminal 2)
bash scripts/pipeline.sh config/examples/direct/bob.sh
```

#### Outsourcing
Computation is delegated to independent MPC nodes. Data owners (Alice, Bob) run matching and input preparation, then send their data live via `client-input.x`. The compute parties run only compilation and the MPC program.

Start the compute parties first (they will wait for client connections):
```bash
# Compute nodes (terminals 1-3)
bash scripts/pipeline.sh config/examples/outsourcing/party0.sh
bash scripts/pipeline.sh config/examples/outsourcing/party1.sh
bash scripts/pipeline.sh config/examples/outsourcing/party2.sh
```
Then run the data owners:
```bash
# Alice (terminal 4)
bash scripts/pipeline.sh config/examples/outsourcing/alice.sh
# Bob (terminal 5)
bash scripts/pipeline.sh config/examples/outsourcing/bob.sh
```


## Development
The project includes a devcontainer configuration (`.devcontainer/`) with all dependencies pre-installed. Open the project in VS Code and select **Reopen in Container** to use it.

The MPC programs in `src/programs/` use MP-SPDZ-specific types and APIs. For code completion in VS Code, add the following to `.vscode/settings.json`:
```json
{
    "python.analysis.extraPaths": ["./MP-SPDZ/"],
    "python.autoComplete.extraPaths": ["./MP-SPDZ/"]
}
```

### Tests
Run the tests:
```bash
python -m pytest tests/ -v
```
> End-to-end tests require the relevant matching binaries to be built.

## About
This project was developed as part of [Evaluating End-to-End MPC Pipelines for Statistical Data Analysis](#) and [Privacy-Preserving Analysis of Misinformation Data](#) with the goal of demonstrating privacy-preserving data analysis using multi-party computation. This is research software and is not intended for production use.
