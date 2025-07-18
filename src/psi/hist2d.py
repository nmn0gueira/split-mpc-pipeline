from Compiler.types import Array, Matrix, sfix, sint, cint, cfix
from Compiler.GC.types import sbitintvec, sbitfixvec
from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler

import pandas as pd


usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

# Options for defining the input matrices and their dimensions
compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the inputs)")
compiler.parse_args()

if not compiler.options.rows:
    compiler.parser.error("--rows required")


def get_bin_edges(values, value_type):
    num_edges = len(values)
    bin_edges = Array(num_edges, value_type)
    previous = float('-inf')
    
    for i in range(num_edges):
        if (values[i] <= previous):
            raise ValueError("Bin edges are not in ascending order")
        bin_edges[i] = value_type(values[i].item())

    return bin_edges


# Binning strategy: edge_1 < x <= edge_2
def digitize(val, bins, bin_edges, secret_type):
    bin_index = secret_type(bins.shape[0] - 1)
    
    # Doing the loop in normal order instead of reverse we do the binning like edge_1 <= x < edge_2
    for i in range(bin_edges.shape[0] - 1, 0, -1):        
        bin_index = mux(val <= bin_edges[i], bins[i-1], bin_index)

    return bin_index


def mux(cond, trueVal, falseVal):
    return cond.if_else(trueVal, falseVal)


def hist_2d(max_rows, edges_df, types):
    """
    Computes a 2D histogram from the input data.
    
    Parameters:
    - max_rows: Maximum number of rows in the input data.
    - edges_df: DataFrame containing the bin edges for both dimensions.
    - types: Tuple containing the types for secret type used in comparisons, clear type used in comparsions, and secret type for histogram values (which only differs between arithmetic and binary circuits).
    """
    secret_type, clear_type, hist_type = types

    bin_edges_x = get_bin_edges(edges_df.iloc[:, 0].values, clear_type)
    bin_edges_y = get_bin_edges(edges_df.iloc[:, 1].values, clear_type)

    num_bins_x = bin_edges_x.shape[0] - 1
    num_bins_y = bin_edges_y.shape[0] - 1

    alice = Array(max_rows, secret_type)
    bob = Array(max_rows, secret_type)

    alice.input_from(0)
    bob.input_from(1)
    
    hist2d = Matrix(num_bins_y, num_bins_x, hist_type)
    hist2d.assign_all(0)

    bins_x = Array(num_bins_x, hist_type)
    for i in range(num_bins_x):
        bins_x[i] = hist_type(i)

    bins_y = Array(num_bins_y, hist_type)
    for i in range(num_bins_y):
        bins_y[i] = hist_type(i)

    
    @for_range_opt(max_rows)
    def _(i):
        bin_index_x = digitize(alice[i], bins_x, bin_edges_x, hist_type)
        bin_index_y = digitize(bob[i], bins_y, bin_edges_y, hist_type)
        
        # For some reason using += instead of regular assignment performs quite a bit better
        for y in range(num_bins_y):
            match_y = bin_index_y == bins_y[y]
            for x in range(num_bins_x):
                hist2d[y][x] += (bin_index_x == bins_x[x]) & match_y # same as mux((bin_index_x == bins_x[x]) & match_y, 1, 0)

    # Reveal the histogram
    print_ln("Histogram 2D:")
    for i in range(num_bins_y):
        for j in range(num_bins_x):
            print_ln("hist2d[%s][%s]: %s", i, j, hist2d[i][j].reveal())


def print_compiler_options(compiler_message):
    print("----------------------------------------------------------------")
    print(compiler_message)
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Rows:", compiler.options.rows)
    print("----------------------------------------------------------------")


@compiler.register_function('hist2d')
def main():
    max_rows = compiler.options.rows

    fixed = 'fix' in compiler.prog.args

    edges_df = pd.read_csv('Player-Data/public/data.csv')
    types = None
    compiler_message = None

    # In binary circuits the only clear type is cbits which does not serve very well for our purposes so the clear_type is equal to the secret_type
    if compiler.prog.options.binary != 0: # If the program is being compiled for binary
        siv = sbitintvec.get_type(int(compiler.prog.options.binary))
        types = (sbitfixvec, sbitfixvec, siv) if fixed else (siv, siv, siv)
        compiler_message = f"Compiling for binary circuits with {types[0]} secret type"

    else:
        compiler.prog.use_trunc_pr = True # Comment this line if the protocol cannot use probabilistic truncation
        types = (sfix, cfix, sint) if fixed else (sint, cint, sint)
        compiler_message = f"Compiling for arithmetic circuits with {types[0]} secret type"

    
    print_compiler_options(compiler_message)

    hist_2d(max_rows, edges_df, types)



if __name__ == "__main__":
    compiler.compile_func()