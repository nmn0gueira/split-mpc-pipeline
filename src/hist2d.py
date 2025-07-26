from Compiler.types import Array, Matrix, sint, sfix
from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
import pandas as pd

usage = "usage: %prog [options]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--n_threads", dest="n_threads", type=int, default=1, help="Number of threads to use for parallel execution")

compiler.parser.add_option("--protocol", dest="protocol", type=str, help="one of psi, cpsi, ps3i, ps3i-xor, pid")
compiler.parser.add_option("--share-type", dest="share_type", type=str, default="xor", help="for cpsi: xor or add32")

compiler.parser.add_option("--rows", dest="rows", type=int, help="max rows")

compiler.parse_args()

if not compiler.options.rows or not compiler.options.protocol:
    compiler.parser.error("--rows and --protocol required")

n_threads = compiler.options.n_threads


def threaded(n_threads, n_loops):
    def decorator(func):
        base = n_loops // n_threads
        remainder = n_loops % n_threads

        def thread_fn(i_thread):
            start = i_thread * base + min(i_thread, remainder)
            end = start + base + (1 if i_thread < remainder else 0)
            @for_range_opt(start, end)
            def _(i):
                func(i, i_thread)

        tapes = [compiler.prog.new_tape(thread_fn, args=[i], single_thread=True)
                 for i in range(n_threads)]
        threads = compiler.prog.run_tapes(tapes)
        compiler.prog.join_tapes(threads)

    return decorator


def mux(cond, true_val, false_val):
    return cond.if_else(true_val, false_val)

def digitize(v, edges):
    idx = sint(0)
    for i in range(len(edges)-1, 0, -1):
        idx = mux(v <= edges[i], i-1, idx)
    return idx


class PsiInput:
    def get(self, rows, secret_type):
        alice = Array(rows, secret_type)
        bob = Array(rows, secret_type)
        alice.input_from(0)
        bob.input_from(1)
        return None, alice, bob

class PrivateIdInput:
    def get(self, rows, secret_type):
        flag = Array(rows, sint)
        alice = Array(rows, secret_type)
        bob = Array(rows, secret_type)
        flag.input_from(0)
        flag *= sint.get_input_from(1, size=rows)
        alice.input_from(0)
        bob.input_from(1)
        return flag, alice, bob

class CircuitPsiInput:
    def __init__(self, share):
        self.share = share
    def get(self, rows, secret_type):
        flag = Array(rows, sint)
        alice = Array(rows, sint)
        bob = Array(rows, secret_type)
        flag.input_from(0)
        flag += sint.get_input_from(1, size=rows)
        flag[:] %= 2
        if self.share == 'add32':
            alice.input_from(0)
            alice += sint.get_input_from(1, size=rows)
            alice[:] %= 2**32
        else:  # xor
            @for_range_opt(rows)
            def _(i):
                alice[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        bob.input_from(1)
        return flag, alice, bob

class CrossPsiInput:
    def get(self, rows, secret_type):
        A = Array(rows, sint)
        B = Array(rows, sint)
        mod = 2**64
        @for_range_opt(rows)
        def _(i):
            A[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod

        @for_range_opt(rows)
        def _(i):
            B[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
        return None, A, B

class CrossPsiXorInput:
    def get(self, rows, secret_type):
        A = Array(rows, sint)
        B = Array(rows, sint)
        @for_range_opt(rows)
        def _(i):
            A[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        @for_range_opt(rows)
        def _(i):
            B[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return None, A, B


def hist2d(flag, input_x, input_y, edges_x, edges_y):    
    nx = len(edges_x)-1
    ny = len(edges_y)-1
    bins_x = range(nx)
    bins_y = range(ny)
    thread_hist2d = sint.Tensor([n_threads, ny, nx])
    
    if flag:
        @threaded(n_threads, input_x.shape[0])
        def _(i, i_thread):
            ix = digitize(input_x[i], edges_x)
            iy = digitize(input_y[i], edges_y)
            for y in bins_y:
                m = (iy==y) * flag[i]
                for x in bins_x:
                    thread_hist2d[i_thread][y][x] += (ix==x) * m
    else:
        @threaded(n_threads, input_x.shape[0])
        def _(i, i_thread):
            ix = digitize(input_x[i], edges_x)
            iy = digitize(input_y[i], edges_y)
            for y in bins_y:
                m = iy==y
                for x in bins_x:
                    thread_hist2d[i_thread][y][x] += (ix==x) * m

    hist2d = Matrix(ny, nx, sint)
    print_ln("Histogram 2D:")
    for y in bins_y:
        for x in bins_x:
            for n in range(n_threads):
                hist2d[y][x] += thread_hist2d[n][y][x]
            print_ln("hist2d[%s][%s]=%s", y, x, hist2d[y][x].reveal())


def print_compiler_options():
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Protocol:", compiler.options.protocol)
    print("Share type (if applicable):", compiler.options.share_type)
    print("Number of threads:", n_threads)
    print("Rows:", compiler.options.rows)
    print("----------------------------------------------------------------")


@compiler.register_function('hist2d')
def main():
    print_compiler_options()
    df = pd.read_csv('Player-Data/public/data.csv', header=None)    # Should contain the edges ordered in two columns
    # Both lists should be of either int or float type depending on the respective input data
    edges_x = df.iloc[:,0].values.tolist()
    edges_y = df.iloc[:,1].values.tolist()
    fact = {
        'psi': PsiInput,
        'pid': PrivateIdInput,
        'cpsi': lambda: CircuitPsiInput(compiler.options.share_type),
        'ps3i': CrossPsiInput,
        'ps3i-xor': CrossPsiXorInput,
    }
    provider = fact[compiler.options.protocol]()
    flag, alice, bob = provider.get(compiler.options.rows, sfix if 'fix' in compiler.prog.args else sint)
    hist2d(flag, alice, bob, edges_x, edges_y)


if __name__ == "__main__":
    compiler.compile_func()
