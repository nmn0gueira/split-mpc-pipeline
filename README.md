# Split MPC Pipeline
This repository contains a practical implementation of a privacy-preserving pipeline using multi-party computation. It focuses on secure dataset matching and subsequent downstream statistical analysis, and is intended as a reference for research and educational purposes. 

The pipeline includes support for protocols such as Circuit-PSI to privately match datasets between parties as well as example MPC programs for use with the MP-SPDZ framework.

## Folder Structure
 - `match/` - Contains submodules implementing protocols for privately matching datasets between parties.
 - `scripts/` - Contains various scripts. Specific scripts mentioned further below.
 - `src/` - Contains source code for the MPC programs used with the MP-SPDZ framework.

 ## Environment Setup
To simplify the build and setup process, a set of scripts is provided alongside a development container (`.devcontainer/`) that includes all required dependencies.

For building all submodules for the project:
```bash
./scripts/build_submodules.sh
```
> Modules are independent. You can install only the ones you wish to experiment wish. Use the `-h` flag with the above script for more info.

You will also need to install MP-SPDZ. For that you can run the following script:
```bash
./scripts/install.sh
```
This will download the latest release binaries on the current directory. If you wish to compile them yourself you can add a `yes` after the above command. This may take a long time, however.


## Usage

### Dataset Matching
> The `geninput.py` script is provided to generate sample data for experimenting.

First, you will need to match datasets between parties. This can be done using the `match.py` wrapper script. The script functions as a frontend for running the protocols used for matching. An example command to run the PSI protocol is:
```bash
python3 scripts/match.py --protocol psi --input path/to/input.csv --output path/to/output.csv --address 127.0.0.1:10010 psi 
```
The input should be a CSV file that contains the identifiers on the first column. The output will be a CSV file containing matched identifiers and any additional data as specified by the protocol.
> For more information on protocol output formats, see [match/README.md](match/README.md).


### Downstream MPC

#### Preparing the required input
Next we need to prepare the input we want for the downstream MPC. This is done using the `iprep.py` script. This script copies the relevant data to the MP-SPDZ directory relevant to the given party, ready to be used for the desired program. An example command to run the script is:
```bash
python3 scripts/iprep.py --input path/to/input.csv --party 0 --columns 0,2,3 --transpose --split --split-ratio 0.8
```
The data to be copied can be adjusted through optional flags such as selecting only specific columns, transposing the data, and splitting the data into training and testing sets.
> For the current programs, usage of the `--transpose` flag is required.

#### Compile-and-run program
Finally, you can specify the downstream MPC program you want to execute. In MP-SPDZ, this means first compiling the program with the appropriate options. For example, to compile a program for executing a 2D histogram computation:
```bash
./scripts/compile.sh hist2d.py -R 64 -Z 2 --rows <num_rows> --protocol <protocol_used_before>
```
> It is necessary to specify the protocol used in the previous phase so the program knows how to handle input.

Afterwards you can run the program as you would any other MP-SPDZ program. Localhost:
```bash
./scripts/run.sh <protocol_script> hist2d
```
or on different terminals:
```bash
./scripts/run.sh <protocol_binary> 0 hist2d
./scripts/run.sh <protocol_binary> 1 hist2d
./scripts/run.sh <protocol_binary> 2 hist2d
```

Available programs include:
- `hist2d`- Computes a 2d histogram.
- `linreg` - Trains a linear regression model.
- `xtabs` - Performs a cross-tabulation. Supports multiple aggregations functions and both 1 and 2 columns to group by.

For more info on a specific program's compilation, use the `--help` flag when compiling.

## About
This project was developed as part of [Privacy-Preserving Analysis of Misinformation Data](nan) with the goal of demonstrating secure data collaboration using multi-party computation.