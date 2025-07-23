from Compiler.types import Array, Matrix, sfix, sint, cint, cfix
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


def get_bin_edges(values):
    num_edges = len(values)
    bin_edges = Array(num_edges, cint)
    previous = float('-inf')
    
    for i in range(num_edges):
        if (values[i] <= previous):
            raise ValueError("Bin edges are not in ascending order")
        bin_edges[i] = cint(int(values[i].item()))

    return bin_edges


def get_input(max_rows):
    alice = Array(max_rows, sint)
    bob = Array(max_rows, sint)
    flag_bits = Array(max_rows, sint)

    @for_range_opt(max_rows)
    def _(i):
        flag_bits[i] = sint.get_input_from(0) * sint.get_input_from(1)
    
    alice.input_from(0)
    bob.input_from(1)

    return flag_bits, alice, bob


# Binning strategy: edge_1 < x <= edge_2
def digitize(val, bin_edges):
    bin_index = sint(0)  # Default bin index if no condition is met
    
    # Doing the loop in normal order instead of reverse we do the binning like edge_1 <= x < edge_2
    for i in range(bin_edges.shape[0] - 1, 0, -1):        
        bin_index = mux(val <= bin_edges[i], i - 1, bin_index)

    return bin_index


def mux(cond, trueVal, falseVal):
    return cond.if_else(trueVal, falseVal)


def hist_2d(max_rows, edges_df):
    """
    Computes a 2D histogram from the input data.
    
    Parameters:
    - max_rows: Maximum number of rows in the input data.
    - edges_df: DataFrame containing the bin edges for both dimensions.
    """

    bin_edges_x = get_bin_edges(edges_df.iloc[:, 0].values)
    bin_edges_y = get_bin_edges(edges_df.iloc[:, 1].values)

    num_bins_x = bin_edges_x.shape[0] - 1
    num_bins_y = bin_edges_y.shape[0] - 1

    flag_bits, alice, bob = get_input(max_rows)

    hist2d = Matrix(num_bins_y, num_bins_x, sint)
    hist2d.assign_all(0)
    
    @for_range_opt(max_rows)
    def _(i):
        bin_index_x = digitize(alice[i], bin_edges_x)
        bin_index_y = digitize(bob[i], bin_edges_y)
        
        # For some reason using += instead of regular assignment performs quite a bit better
        for y in range(num_bins_y):
            match_y = (bin_index_y == y) * flag_bits[i]
            for x in range(num_bins_x):
                hist2d[y][x] += (bin_index_x == x) * match_y

    print_ln("Histogram 2D:")
    for i in range(num_bins_y):
        for j in range(num_bins_x):
            print_ln("hist2d[%s][%s]: %s", i, j, hist2d[i][j].reveal())


def print_compiler_options():
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Rows:", compiler.options.rows)
    print("----------------------------------------------------------------")


@compiler.register_function('hist2d')
def main():
    max_rows = compiler.options.rows
    edges_df = pd.read_csv('Player-Data/public/data.csv', header=None)

    print_compiler_options()
    hist_2d(max_rows, edges_df)


if __name__ == "__main__":
    compiler.compile_func()