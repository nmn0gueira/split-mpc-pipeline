from Compiler.types    import Array, Matrix, sint, cint
from Compiler.library  import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
import pandas as pd

usage = "usage: %prog [options]"
compiler = Compiler(usage=usage)
compiler.parser.add_option("--rows",     dest="rows",       type=int, help="max rows")
compiler.parser.add_option("--protocol", dest="protocol",   type=str,
                          help="one of psi, cpsi, ps3i, ps3i-xor, pid")
compiler.parser.add_option("--share-type", dest="share_type", type=str,
                          default="xor", help="for cpsi: xor or add32")
compiler.parse_args()
if not compiler.options.rows or not compiler.options.protocol:
    compiler.parser.error("--rows and --protocol required")


def get_bin_edges(values):
    N = len(values)
    edges = Array(N, cint)
    prev = float('-inf')
    for i,val in enumerate(values):
        if val <= prev:
            raise ValueError("Edges must ascend")
        edges[i] = cint(int(val))
        prev = val
    return edges

def mux(c, t, f): return c.if_else(t, f)

def digitize(v, edges):
    idx = sint(0)
    N = edges.shape[0]
    for i in range(N-1, 0, -1):
        idx = mux(v <= edges[i], i-1, idx)
    return idx


class PsiInput:
    def get(self, R):
        A = Array(R, sint)
        B = Array(R, sint)
        A.input_from(0); B.input_from(1)
        return None, A, B

class PrivateIdInput:
    def get(self, R):
        flag = Array(R, sint)
        A = Array(R, sint)
        B = Array(R, sint)
        @for_range_opt(R)
        def _(i):
            flag[i] = sint.get_input_from(0) * sint.get_input_from(1)
        A.input_from(0); B.input_from(1)
        return flag, A, B

class CircuitPsiInput:
    def __init__(self, share):
        self.share = share
    def get(self, R):
        flag = Array(R, sint)
        A = Array(R, sint)
        B = Array(R, sint)
        @for_range_opt(R)
        def _(i):
            flag[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % 2
        if self.share == 'add32':
            mod = 2**32
            @for_range_opt(R)
            def _(i):
                A[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
        else:  # xor
            @for_range_opt(R)
            def _(i):
                A[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        B.input_from(1)
        return flag, A, B

class CrossPsiInput:
    def get(self, R):
        A = Array(R, sint)
        B = Array(R, sint)
        mod = 2**64
        @for_range_opt(R)
        def _(i):
            A[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod

        @for_range_opt(R)
        def _(i):
            B[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
        return None, A, B

class CrossPsiXorInput:
    def get(self, R):
        A = Array(R, sint)
        B = Array(R, sint)
        @for_range_opt(R)
        def _(i):
            A[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        @for_range_opt(R)
        def _(i):
            B[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return None, A, B


fact = {
    'psi':      PsiInput,
    'pid':  PrivateIdInput,
    'cpsi':  lambda: CircuitPsiInput(compiler.options.share_type),
    'ps3i':    CrossPsiInput,
    'ps3i-xor':CrossPsiXorInput,
}
provider = fact[compiler.options.protocol]()


def hist2d(flag, input_x, input_y, edges_x, edges_y):
    num_rows = input_x.shape[0]
    assert num_rows == input_y.shape[0], "input_x and input_y must have the same number of rows"
    
    nx = edges_x.shape[0]-1
    ny = edges_y.shape[0]-1
    bins_x = range(nx)
    bins_y = range(ny)
    hist2d = Matrix(ny, nx, sint)
    
    if flag:
        @for_range_opt(num_rows)
        def _(i):
            ix = digitize(input_x[i], edges_x)
            iy = digitize(input_y[i], edges_y)
            for y in bins_y:
                m = (iy==y) * flag[i]
                for x in bins_x:
                    hist2d[y][x] += (ix==x) * m
    else:
        @for_range_opt(num_rows)
        def _(i):
            ix = digitize(input_x[i], edges_x)
            iy = digitize(input_y[i], edges_y)
            for y in bins_y:
                m = iy==y
                for x in bins_x:
                    hist2d[y][x] += (ix==x) * m

    print_ln("Histogram 2D:")
    for y in bins_y:
        for x in bins_x:
            print_ln("hist2d[%s][%s]=%s", y, x, hist2d[y][x].reveal())


def print_compiler_options():
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Rows:", compiler.options.rows)
    print("Protocol:", compiler.options.protocol)
    print("Share type (if applicable):", compiler.options.share_type)
    print("----------------------------------------------------------------")


@compiler.register_function('hist2d')
def main():
    print_compiler_options()
    df = pd.read_csv('Player-Data/public/data.csv', header=None)
    edges_x = get_bin_edges(df.iloc[:,0].values)
    edges_y = get_bin_edges(df.iloc[:,1].values)
    
    flag, alice, bob = provider.get(compiler.options.rows)
    hist2d(flag, alice, bob, edges_x, edges_y)


if __name__ == "__main__":
    compiler.compile_func()
