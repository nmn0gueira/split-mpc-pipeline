from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
from Compiler.mpc_math import sqrt
from Compiler.types import sint, sfix, Array, Matrix

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--n_threads", dest="n_threads", type=int, default=1, help="Number of threads to use for parallel execution")

compiler.parser.add_option("--protocol", dest="protocol", type=str, help="one of psi, cpsi, ps3i, ps3i-xor, pid")
compiler.parser.add_option("--share-type", dest="share_type", type=str, default="xor", help="for cpsi: xor or add32")

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices")
compiler.parser.add_option("--n_cat_1", dest="n_cat_1", default=4, type=int, help="Number of categories for the first aggregation column")
compiler.parser.add_option("--n_cat_2", dest="n_cat_2", default=4, type=int, help="Number of categories for the second aggregation column (if applicable)")

compiler.parser.add_option("--aggregation", dest="aggregation", type=str, help="Type of aggregation to be performed (sum, avg, freq, mode, std")
compiler.parser.add_option("--group_by", dest="group_by", type=str, help="Columns to group by (2 max) (e.g ab for Alice's first column and Bob's first column")
compiler.parser.add_option("--values", dest="values", type=str, help="Value column (not needed for mode and freq.) (e.g b for Bob's column)")

compiler.parse_args()

if not compiler.options.rows:
    compiler.parser.error("--rows")

n_threads = compiler.options.n_threads
function_name = f"xtabs-{compiler.options.aggregation}-{len(compiler.options.group_by)}"    # e.g. xtabs-sum-2


def threaded(n_threads, n_loops):
    """
    Decorator to parallelize a function across multiple threads. Works with non-uniform thread distribution.
    """
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


def mux(cond, trueVal, falseVal):
    return cond.if_else(trueVal, falseVal)


def parse_column_spec(column_spec):
    alice_cols = bob_cols = 0
    for ch in column_spec:
        if ch == 'a':
            alice_cols += 1
        elif ch == 'b':
            bob_cols += 1
        else:
            raise ValueError(f"Unexpected column format: {column_spec}")
    return alice_cols, bob_cols


def get_array(rows, party, secret_type):
    party = 0 if party == 'a' else 1
    array = Array(rows, secret_type)
    array.input_from(party)
    return array


def get_matrix(rows, column_spec, secret_type):
    alice_cols, bob_cols = parse_column_spec(column_spec)
    matrix = Matrix(rows, len(column_spec), secret_type)

    for i in range(alice_cols):
        matrix.set_column(i, secret_type.get_input_from(0, size=rows)) 

    for i in range(bob_cols):
        matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows)) 
    
    return matrix


class PsiInput:
    def get_flag(self, rows):
        return None
    
    def get_array(self, rows, party, secret_type):
        party = 0 if party == 'a' else 1
        array = Array(rows, secret_type)
        array.input_from(party)
        return array

    def get_matrix(self, rows, column_spec, secret_type):
        alice_cols, bob_cols = parse_column_spec(column_spec)
        matrix = Matrix(rows, len(column_spec), secret_type)
        for i in range(alice_cols):
            matrix.set_column(i, secret_type.get_input_from(0, size=rows)) 
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows))    
        return matrix

class PrivateIdInput:
    def get_flag(self, rows):
        flag = Array(rows, sint)
        @for_range_opt(rows)
        def _(i):
            flag[i] = sint.get_input_from(0) * sint.get_input_from(1)
        return flag
    
    def get_array(self, rows, party, secret_type):
        party = 0 if party == 'a' else 1
        array = Array(rows, secret_type)
        array.input_from(party)
        return array

    def get_matrix(self, rows, column_spec, secret_type):
        alice_cols, bob_cols = parse_column_spec(column_spec)
        matrix = Matrix(rows, len(column_spec), secret_type)
        for i in range(alice_cols):
            matrix.set_column(i, secret_type.get_input_from(0, size=rows)) 
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows))    
        return matrix

class CircuitPsiInput:
    def __init__(self, share):
        self.share = share

    def get_flag(self, rows):
        flag = Array(rows, sint)
        @for_range_opt(rows)
        def _(i):
            flag[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % 2
        return flag
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        if party == 'a':
            if self.share == 'add32':
                mod = 2**32
                @for_range_opt(rows)
                def _(i):
                    array[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
            else:
                @for_range_opt(rows)
                def _(i):
                    array[i] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
        else:  # party == 'b'
            array.input_from(1)
        return array

    def get_matrix(self, rows, column_spec, secret_type):
        alice_cols, bob_cols = parse_column_spec(column_spec)
        matrix = Matrix(rows, len(column_spec), secret_type)
        for i in range(alice_cols):
            tmp_array = secret_type.Array(rows)
            if self.share == 'add32':
                mod = 2**32
                @for_range_opt(rows)
                def _(j):
                    tmp_array[j] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
            else:
                @for_range_opt(rows)
                def _(j):
                    tmp_array[j] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
            matrix.set_column(i, tmp_array)
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows))    
        return matrix

class CrossPsiInput:
    def get_flag(self, rows):
        return None
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        mod = 2**64
        @for_range_opt(rows)
        def _(i):
            array[i] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
        return array

    def get_matrix(self, rows, column_spec, secret_type):
        matrix = Matrix(rows, len(column_spec), secret_type)
        mod = 2**64
        for i in range(len(column_spec)):
            tmp_array = secret_type.Array(rows)
            @for_range_opt(rows)
            def _(j):
                tmp_array[j] = (sint.get_input_from(0) + sint.get_input_from(1)) % mod
            matrix.set_column(i, tmp_array) 
        return matrix

class CrossPsiXorInput:
    def get_flag(self, rows):
        return None
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        @for_range_opt(rows)
        def _(i):
            array[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return array

    def get_matrix(self, rows, column_spec, secret_type):
        matrix = Matrix(rows, len(column_spec), secret_type)
        for i in range(len(column_spec)):
            tmp_array = secret_type.Array(rows)
            @for_range_opt(rows)
            def _(j):
                tmp_array[j] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
            matrix.set_column(i, tmp_array) 
        return matrix


def xtabs_sum1(flag, group_by, values, stype_val, cat_len):
    thread_sums = stype_val.Tensor([n_threads, cat_len])
    categories = range(cat_len)

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            value = flag[i] * values[i]
            for cat in categories:
                thread_sums[i_thread][cat] += (group_by[i] == cat) * value
    
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat in categories:
                thread_sums[i_thread][cat] += (group_by[i] == cat) * values[i]
    
    sums = Array(cat_len, stype_val)
    for cat in categories:
        for n in range(n_threads):
            sums[cat] += thread_sums[n][cat]
        print_ln("Sum %s: %s", cat, sums[cat].reveal())


def xtabs_sum2(flag, group_by, values, stype_val, cat_len_1, cat_len_2):
    thread_sums = stype_val.Tensor([n_threads, cat_len_1, cat_len_2])
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)


    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            value = flag[i] * values[i]
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    thread_sums[i_thread][cat_1][cat_2] += (match_1 & (group_by[i][1] == cat_2)) * value
    
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    thread_sums[i_thread][cat_1][cat_2] += (match_1 & (group_by[i][1] == cat_2)) * values[i]

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                sums[cat_1][cat_2] += thread_sums[n][cat_1][cat_2]
            print_ln("Sum (%s, %s): %s", cat_1, cat_2, sums[cat_1][cat_2].reveal())


def xtabs_avg1(flag, group_by, values, stype_val, cat_len):
    thread_sums = stype_val.Tensor([n_threads, cat_len])
    thread_counts = sint.Tensor([n_threads, cat_len])
    categories = range(cat_len)

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            #value = flag[i] * values[i]    Cannott use just this as the counts cannot make use of this to economize computation/comm needed
            for cat in categories:
                full_match = (group_by[i] == cat) * flag[i]
                thread_sums[i_thread][cat] += full_match * values[i]
                thread_counts[i_thread][cat] += full_match
    
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat in categories:
                full_match = group_by[i] == cat
                thread_sums[i_thread][cat] += full_match * values[i]
                thread_counts[i_thread][cat] += full_match

    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    for cat in categories:
        for n in range(n_threads):
            sums[cat] += thread_sums[n][cat]
            counts[cat] += thread_counts[n][cat]
        print_ln("Avg %s: %s", cat, (sums[cat] / counts[cat]).reveal())


def xtabs_avg2(flag, group_by, values, stype_val, cat_len_1, cat_len_2):
    thread_sums = stype_val.Tensor([n_threads, cat_len_1, cat_len_2])
    thread_counts = sint.Tensor([n_threads, cat_len_1, cat_len_2])
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    if flag:
        @threaded(n_threads,  group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = (group_by[i][0] == cat_1) * flag[i]
                for cat_2 in categories_2:
                    full_match = match_1 & (group_by[i][1] == cat_2)
                    thread_sums[i_thread][cat_1][cat_2] += full_match * values[i]
                    thread_counts[i_thread][cat_1][cat_2] += full_match

    else:
        @threaded(n_threads,  group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    full_match = match_1 & (group_by[i][1] == cat_2)
                    thread_sums[i_thread][cat_1][cat_2] += full_match * values[i]
                    thread_counts[i_thread][cat_1][cat_2] += full_match
    
    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                sums[cat_1][cat_2] += thread_sums[n][cat_1][cat_2]
                counts[cat_1][cat_2] += thread_counts[n][cat_1][cat_2]
            print_ln("Avg (%s, %s): %s", cat_1, cat_2, (sums[cat_1][cat_2] / counts[cat_1][cat_2]).reveal())


def xtabs_std1(flag, group_by, values, stype_val, cat_len, ddof=0):
    thread_sums = stype_val.Tensor([n_threads, cat_len])
    thread_counts = sint.Tensor([n_threads, cat_len])
    thread_variances = sint.Tensor([n_threads, cat_len])
    categories = range(cat_len)

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            #value = flag[i] * values[i]    Cannott use just this as the counts cannot make use of this to economize computation/comm needed
            for cat in categories:
                full_match = (group_by[i] == cat) * flag[i]
                thread_sums[i_thread][cat] += full_match * values[i]
                thread_counts[i_thread][cat] += full_match
    
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat in categories:
                full_match = group_by[i] == cat
                thread_sums[i_thread][cat] += full_match * values[i]
                thread_counts[i_thread][cat] += full_match
    
    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    averages = Array(cat_len, sfix)
    for cat in categories:
        for n in range(n_threads):
            sums[cat] += thread_sums[n][cat]
            counts[cat] += thread_counts[n][cat]
        averages[cat] = sums[cat] / counts[cat]

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat in categories:
                thread_variances[i_thread][cat] += (group_by[i] == cat) * ((values[i] - averages[cat]) ** 2) * flag[i]
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat in categories:
                thread_variances[i_thread][cat] += (group_by[i] == cat) * ((values[i] - averages[cat]) ** 2)

    variances = Array(cat_len, sfix)
    for cat in categories:
        for n in range(n_threads):
            variances[cat] += thread_variances[n][cat]
        print_ln("Std %s: %s", cat, sqrt(variances[cat] / (counts[cat] - ddof)).reveal())


def xtabs_std2(flag, group_by, values, stype_val, cat_len_1, cat_len_2, ddof=0):
    thread_sums = stype_val.Tensor([n_threads, cat_len_1, cat_len_2])
    thread_counts = sint.Tensor([n_threads, cat_len_1, cat_len_2])
    thread_variances = sfix.Tensor([n_threads, cat_len_1, cat_len_2])
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)  

    if flag:
        @threaded(n_threads,  group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = (group_by[i][0] == cat_1) * flag[i]
                for cat_2 in categories_2:
                    full_match = match_1 & (group_by[i][1] == cat_2)
                    thread_sums[i_thread][cat_1][cat_2] += full_match * values[i]
                    thread_counts[i_thread][cat_1][cat_2] += full_match

    else:
        @threaded(n_threads,  group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    full_match = match_1 & (group_by[i][1] == cat_2)
                    thread_sums[i_thread][cat_1][cat_2] += full_match * values[i]
                    thread_counts[i_thread][cat_1][cat_2] += full_match

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    averages = Matrix(cat_len_1, cat_len_2, sfix)

    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                sums[cat_1][cat_2] += thread_sums[n][cat_1][cat_2]
                counts[cat_1][cat_2] += thread_counts[n][cat_1][cat_2]
            averages[cat_1][cat_2] = sums[cat_1][cat_2] / counts[cat_1][cat_2]

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = (group_by[i][0] == cat_1) * flag[i]
                for cat_2 in categories_2:
                    thread_variances[i_thread][cat_1][cat_2] += (match_1 & (group_by[i][1] == cat_2)) * ((values[i] - averages[cat_1][cat_2]) ** 2)
    
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    thread_variances[i_thread][cat_1][cat_2] += (match_1 & (group_by[i][1] == cat_2)) * ((values[i] - averages[cat_1][cat_2]) ** 2)
    
    variances = Matrix(cat_len_1, cat_len_2, sfix)
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                variances[cat_1][cat_2] += thread_variances[n][cat_1][cat_2]
            print_ln("Std (%s, %s): %s", cat_1, cat_2, sqrt(variances[cat_1][cat_2] / (counts[cat_1][cat_2] - ddof)).reveal())


def xtabs_freq(flag, group_by, cat_len_1, cat_len_2):
    thread_counts = sint.Tensor([n_threads, cat_len_1, cat_len_2])
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = (group_by[i][0] == cat_1) * flag[i]
                for cat_2 in categories_2:
                    thread_counts[i_thread][cat_1][cat_2] += match_1 & (group_by[i][1] == cat_2)
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    thread_counts[i_thread][cat_1][cat_2] += match_1 & (group_by[i][1] == cat_2)

    counts = Matrix(cat_len_1, cat_len_2, sint)
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                counts[cat_1][cat_2] += thread_counts[n][cat_1][cat_2]
            print_ln("Freq (%s, %s): %s", cat_1, cat_2, counts[cat_1][cat_2].reveal())


def xtabs_mode(flag, group_by, cat_len_1, cat_len_2):
    thread_counts = sint.Tensor([n_threads, cat_len_1, cat_len_2])
    modes = Array(cat_len_1, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    if flag:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = (group_by[i][0] == cat_1) * flag[i]
                for cat_2 in categories_2:
                    thread_counts[i_thread][cat_1][cat_2] += match_1 & (group_by[i][1] == cat_2)
    else:
        @threaded(n_threads, group_by.shape[0])
        def _(i, i_thread):
            for cat_1 in categories_1:
                match_1 = group_by[i][0] == cat_1
                for cat_2 in categories_2:
                    thread_counts[i_thread][cat_1][cat_2] += match_1 & (group_by[i][1] == cat_2)

    counts = Matrix(cat_len_1, cat_len_2, sint)
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            for n in range(n_threads):
                counts[cat_1][cat_2] += thread_counts[n][cat_1][cat_2]
    
    for cat_1 in categories_1:
        max_value = sint(0)
        mode = sint(-1)
        for cat_2 in categories_2:
            geq = counts[cat_1][cat_2] > max_value
            max_value = mux(geq, counts[cat_1][cat_2], max_value)
            eq_max = counts[cat_1][cat_2] == max_value
            mode = mux(eq_max, cat_2, mode)
        modes[cat_1] = mode

    for cat_1 in categories_1:
        print_ln("Mode %s: %s", cat_1, modes[cat_1].reveal())


def xtabs_1(aggregation, flag, group_by, values, stype_val, cat_len):
    if aggregation == 'sum':
        xtabs_sum1(flag, group_by, values, stype_val, cat_len)
    elif aggregation == 'avg':
        xtabs_avg1(flag, group_by, values, stype_val, cat_len)
    elif aggregation == 'std':
        xtabs_std1(flag, group_by, values, stype_val, cat_len)
    elif aggregation == 'freq':
        raise ValueError("Frequency aggregation not supported for single column")
    elif aggregation == 'mode':
        raise ValueError("Mode aggregation not supported for single column")
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def xtabs_2(aggregation, flag, group_by, values, stype_val, cat_len_1, cat_len_2):
    if aggregation == 'sum':
        xtabs_sum2(flag, group_by, values, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'avg':
        xtabs_avg2(flag, group_by, values, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'std':
        xtabs_std2(flag, group_by, values, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'freq':
        xtabs_freq(flag, group_by, cat_len_1, cat_len_2)
    elif aggregation == 'mode':
        xtabs_mode(flag, group_by, cat_len_1, cat_len_2)
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def print_compiler_options():
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Protocol:", compiler.options.protocol)
    print("Share type:", compiler.options.share_type)
    print("Number of threads:", n_threads)
    print("Rows:", compiler.options.rows)
    print("Number of categories for first column:", compiler.options.n_cat_1)
    print("Number of categories for second column (if applicable):", compiler.options.n_cat_2)
    print("Aggregation type:", compiler.options.aggregation)
    print("Group by columns:", compiler.options.group_by)
    print("Value column (if applicable):", compiler.options.values)
    print("----------------------------------------------------------------")


@compiler.register_function(function_name)
def main():
    fact = {
        'psi':      PsiInput,
        'pid':  PrivateIdInput,
        'cpsi':  lambda: CircuitPsiInput(compiler.options.share_type),
        'ps3i':    CrossPsiInput,
        'ps3i-xor':CrossPsiXorInput,
    }

    provider = fact[compiler.options.protocol]()
    num_group_by = len(compiler.options.group_by)

    compiler.prog.use_trunc_pr = True
    stype_val = sfix if 'fix' in compiler.prog.args else sint

    print_compiler_options()

    if num_group_by == 1:
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_array(compiler.options.rows, compiler.options.group_by, sint)
        values = provider.get_array(compiler.options.rows, compiler.options.values, stype_val)
        xtabs_1(compiler.options.aggregation, flag, group_by, values, stype_val, compiler.options.n_cat_1)

    elif num_group_by == 2:
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_matrix(compiler.options.rows, compiler.options.group_by, sint)
        values = provider.get_array(compiler.options.rows, compiler.options.values, stype_val) if compiler.options.values else None
        xtabs_2(compiler.options.aggregation, flag, group_by, values, stype_val, compiler.options.n_cat_1, compiler.options.n_cat_2)
    else:
        raise ValueError(f"Unsupported number of columns to group by: {num_group_by}")


if __name__ == "__main__":
    compiler.compile_func()