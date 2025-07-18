# This file is used to generate MP-SPDZ input from csv files
from Compiler.types import sint
from Compiler.compilerLib import Compiler

import pandas as pd
from sklearn.model_selection import train_test_split

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

# Options for defining the input matrices and their dimensions
compiler.parser.add_option("--columns", dest="columns", type=str, help="Columns to be used")

# Split options
compiler.parser.add_option("--test_size", dest="test_size", default=0.2, type=float, help="Proportion of the dataset to include in the test split (default: 0.2)")
compiler.parser.add_option("--random_state", dest="random_state", default=42, type=int, help="Random seed for reproducibility (default: 42)")
compiler.parse_args()

# TODO
# Maybe think of adding a way to store this input in other places for reuse between using other programs if it turns out to be useful
# Add an option to scale features and normalize labels in here, if necessary.

# Storing using sint and binary=False (raw data) seems to work with every type needed in a program
def store_df(df, party, by_column):
    if by_column:  # Store each column as a separate tensor (this helps optimize memory when performing linear regression, for example)
        for col in df.columns:
            sint.input_tensor_via(party, df[col].values, binary=False)
    else:
        sint.input_tensor_via(party, df.values, binary=False)

def csv2spdz(path, party, columns, split, by_column):
    df = pd.read_csv(path)

    if columns:
        # Convert columns to a list of integers if they are provided as indices
        if isinstance(columns, str):
            columns = [int(col) for col in columns.split(',')]
        df = df.iloc[:, columns]
        print(f"Selected columns for party {party}: {columns}")
    
    if split:
        df_train, df_test = train_test_split(df, test_size=compiler.options.test_size, random_state=compiler.options.random_state) # Use shuffle=False if debugging
        store_df(df_train, party, by_column)
        store_df(df_test, party, by_column)
        print(f"Input data for party {party}: {df_train.shape[0]} training samples, {df_test.shape[0]} test samples.")
    else:
        store_df(df, party, by_column)
        print(f"Input data for party {party}: {df.shape[0]} samples.")

    print(f"Data stored by column: {by_column}")
    print(f"Columns: {columns if columns else 'all'}")
    

# Parsing this way will not allow to specify columns with more than one digit, e.g., a10b1 which is irrelevant for now but still
def parse_columns(columns):
    a_columns = []
    b_columns = []
    for i in range(0, len(columns), 2):
        if columns[i] == 'a':
            a_columns.append(int(columns[i + 1]))
        elif columns[i] == 'b':
            b_columns.append(int(columns[i + 1]))
    return a_columns, b_columns


@compiler.register_function('csv2spdz')
def main():
    split = 'split' in compiler.prog.args
    by_column = 'by_column' in compiler.prog.args

    a_columns, b_columns = parse_columns(compiler.options.columns) if compiler.options.columns else (None, None)

    if 'party0' in compiler.prog.args:
        csv2spdz('Player-Data/alice/data.csv', 0, a_columns, split, by_column)
    if 'party1' in compiler.prog.args:
        csv2spdz('Player-Data/bob/data.csv', 1, b_columns, split, by_column)
        

if __name__ == "__main__":
    compiler.compile_func()