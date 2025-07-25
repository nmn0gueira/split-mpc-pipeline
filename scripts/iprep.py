import argparse
import pandas as pd
from sklearn.model_selection import train_test_split
import sys


def transform_csv(input_file, output_dir, party, columns=None, transpose=False, do_split=False, split_ratio=0.8):
    try:
        df = pd.read_csv(input_file, header=None, dtype=object)
        num_inputs = len(df)

        if columns is not None:
            df = df.iloc[:, columns]

        if do_split:
            train_df, test_df = train_test_split(df, train_size=split_ratio, shuffle=True, random_state=42)
            df = pd.concat([train_df, test_df])
        
        if transpose:
            df = df.transpose()

        output_file = f"{output_dir}/Input-P{party}-0"
        df.to_csv(output_file, sep=' ', index=False, header=False)
        print(f"Successfully wrote {num_inputs} lines to {output_file}")

    except Exception as e:
        print(f"Error during transformation: {e}", file=sys.stderr)
        sys.exit(1)


def parse_columns(column_str):
    try:
        return [int(c) for c in column_str.split(',')]
    except ValueError:
        raise argparse.ArgumentTypeError("Columns must be a comma-separated list of integers (e.g., 0,1,3)")


def main():
    parser = argparse.ArgumentParser(description="Input preparation script for use with MP-SPDZ")
    parser.add_argument("--input", type=str, required=True, help="Path to input CSV file")
    parser.add_argument("--output_dir", type=str, default='MP-SPDZ/Player-Data', help="Directory to output the file(s) (default: MP-SPDZ/Player-Data)")
    parser.add_argument("--party", type=int, required=True, help="Party number")
    parser.add_argument("--columns", type=parse_columns, help="Comma-separated list of column indices (e.g., 0,2,3)")
    parser.add_argument("--transpose", action="store_true", help="Transpose the output CSV")
    parser.add_argument("--split", action="store_true", help="Split into train/test and append test after train")
    parser.add_argument("--split-ratio", type=float, default=0.8, help="Train/test split ratio (default: 0.8)")
    #parser.add_argument("--num-files", type=int, default=1, help="Number of output files to split the data into")

    args = parser.parse_args()
    transform_csv(
        args.input,
        args.output_dir,
        args.party,
        columns=args.columns,
        transpose=args.transpose,
        do_split=args.split,
        split_ratio=args.split_ratio
    )


if __name__ == "__main__":
    main()
