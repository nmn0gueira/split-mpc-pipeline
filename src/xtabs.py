from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
from Compiler.mpc_math import sqrt
from Compiler.types import sint, sfix, Array, Matrix, sintbit

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--protocol", dest="protocol", type=str, help="one of psi, cpsi, ps3i, ps3i-xor, pid")
compiler.parser.add_option("--share-type", dest="share_type", type=str, default="xor", help="for cpsi: xor or add32")

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices")
compiler.parser.add_option("--n_cat_1", dest="n_cat_1", default=4, type=int, help="Number of categories for the first aggregation column")
compiler.parser.add_option("--n_cat_2", dest="n_cat_2", default=4, type=int, help="Number of categories for the second aggregation column (if applicable)")

compiler.parser.add_option("--aggregation", dest="aggregation", type=str, help="Type of aggregation to be performed (sum, avg, freq, mode, std")
compiler.parser.add_option("--group_by", dest="group_by", type=str, help="Columns to group by (2 max) (e.g ab for Alice's first column and Bob's first column")
compiler.parser.add_option("--values", dest="values", type=str, help="Value column (not needed for mode and freq.) (e.g b for Bob's column)")

compiler.parse_args()

if not compiler.options.rows or not compiler.options.protocol:
    compiler.parser.error("--rows and --protocol required")

function_name = f"xtabs-{compiler.options.aggregation}-{len(compiler.options.group_by)}"    # e.g. xtabs-sum-2


def mux(cond, true_val, false_val):
    return cond.if_else(true_val, false_val)


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

def get_party_from_char(ch):
    if ch == 'a':
        return 0
    elif ch == 'b':
        return 1
    else:
        raise ValueError(f"Unexpected character in group_by: {ch}")

class PsiInput:
    def get_flag(self, rows):
        return None
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        array.input_from(party)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, sint)
        for i in range(alice_cols):
            matrix.set_column(i, sint.get_input_from(0, size=rows)) 
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, sint.get_input_from(1, size=rows))    
        return matrix

class PrivateIdInput:
    def get_flag(self, rows):
        flag = Array(rows, sintbit)
        flag.input_from(0)
        flag[:] &= sintbit.get_input_from(1, size=rows)   
        return flag
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        array.input_from(party)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, sint)
        for i in range(alice_cols):
            matrix.set_column(i, sint.get_input_from(0, size=rows)) 
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, sint.get_input_from(1, size=rows))    
        return matrix

class CircuitPsiInput:
    def __init__(self, share):
        self.share = share

    def get_flag(self, rows):
        flag = Array(rows, sintbit)
        flag.input_from(0)
        flag[:] ^= sintbit.get_input_from(1, size=rows)
        return flag
    
    def get_array(self, rows, party, secret_type):
        if party == 0:
            array = Array(rows, secret_type)
            if self.share == 'add32':
                array[:] = (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % 2**32
            else:
                @for_range_opt(rows)
                def _(i):
                    array[i] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
        else:  # party == 'b'
            array = Array(rows, secret_type)
            array.input_from(1)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, sint)
        mod = 2**32
        for i in range(alice_cols):
            if self.share == 'add32':
                matrix.set_column(i, (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % mod)
            else:
                @for_range_opt(rows)
                def _(j):
                    matrix[j][i] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, sint.get_input_from(1, size=rows))    
        return matrix

class CrossPsiInput:
    def get_flag(self, rows):
        return None
    
    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        array[:] = (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % 2**64
        return array

    def get_matrix(self, rows, alice_cols, bob_cols):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, sint)
        mod = 2**64
        for i in range(num_cols):
            matrix.set_column(i, (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % mod)
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

    def get_matrix(self, rows, alice_cols, bob_cols):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, sint)
        for i in range(num_cols):
            @for_range_opt(rows)
            def _(j):
                matrix[j][i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return matrix


def xtabs_sum1(flag, group_by, values, stype_val, cat_len):
    sums = Array(cat_len, stype_val)
    categories = range(cat_len)
    values = values * flag if flag else values
    for i in categories:
        sums[i] = ((group_by == i) * values).sum()
    
    for cat in categories:
        print_ln("Sum %s: %s", cat, sums[cat].reveal())


def xtabs_sum2(flag, group_by, values, stype_val, cat_len_1, cat_len_2):
    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    values = values * flag if flag else values
    eq_cat_2 = [group_by.get_column(1) == j for j in categories_2]
    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            sums[i][j] = ((eq_cat_1 & eq_cat_2[j]) * values).sum()

    
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            print_ln("Sum (%s, %s): %s", cat_1, cat_2, sums[cat_1][cat_2].reveal())


def xtabs_avg1(flag, group_by, values, stype_val, cat_len):
    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    group_by = group_by * flag if flag else group_by
    eq_cat = [(group_by == i) for i in range(1, cat_len + 1)]
    
    for i in range(sums.shape[0]):
        sums[i] = (eq_cat[i] * values).sum()
        counts[i] = eq_cat[i].sum()
        print_ln("Avg %s: %s", i + 1, (sums[i] / counts[i]).reveal())


def xtabs_avg2(flag, group_by, values, stype_val, cat_len_1, cat_len_2):
    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    if flag:
        group_by.set_column(0, group_by.get_column(0) * flag)
    eq_cat_2 = [(group_by.get_column(1) == j) for j in range(1, cat_len_2 + 1)]

    for i in range(sums.shape[0]):
        eq_cat_1 = group_by.get_column(0) == i + 1
        for j in range(sums.shape[1]):
            full_match = eq_cat_1 * eq_cat_2[j]
            sums[i][j] = (full_match * values).sum()
            counts[i][j] = full_match.sum()
            print_ln("Avg (%s, %s): %s", i + 1, j + 1, (sums[i][j] / counts[i][j]).reveal())


def xtabs_std1(flag, group_by, values, stype_val, cat_len, ddof=0):
    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    averages = Array(cat_len, sfix)
    variances = Array(cat_len, sfix)
    categories = range(cat_len)
    eq_cat = [(group_by == i) * flag for i in categories] if flag else [(group_by == i) for i in categories]

    for i in categories:
        sums[i] = (eq_cat[i] * values).sum()
        counts[i] = eq_cat[i].sum()
        averages[i] = sums[i] / counts[i]
        variances[i] = (eq_cat[i] * (values - averages[i])**2).sum()
    
    for cat in categories:
        print_ln("Std %s: %s", cat, sqrt(variances[cat] / (counts[cat] - ddof)).reveal())


def xtabs_std2(flag, group_by, values, stype_val, cat_len_1, cat_len_2, ddof=0):
    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    averages = Matrix(cat_len_1, cat_len_2, sfix)
    variances = Matrix(cat_len_1, cat_len_2, sfix)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)  

    eq_cat_2 = [(group_by.get_column(1) == j) * flag for j in categories_2] if flag else [(group_by.get_column(1) == j) for j in categories_2]

    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            full_match = eq_cat_1 * eq_cat_2[j]
            sums[i][j] = (full_match * values).sum()
            counts[i][j] = full_match.sum()
            averages[i][j] = sums[i][j] / counts[i][j]
            variances[i][j] = (full_match * (values - averages[i][j])**2).sum()


    for cat_1 in categories_1:
        for cat_2 in categories_2:
            print_ln("Std (%s, %s): %s", cat_1, cat_2, sqrt(variances[cat_1][cat_2] / (counts[cat_1][cat_2] - ddof)).reveal())


def xtabs_freq(flag, group_by, cat_len_1, cat_len_2):
    counts = Matrix(cat_len_1, cat_len_2, sint)    
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)
    eq_cat_2 = [(group_by.get_column(1) == j) * flag for j in categories_2] if flag else [(group_by.get_column(1) == j) for j in categories_2]
    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            counts[i][j] = (eq_cat_1 * eq_cat_2[j]).sum()
    
    for cat_1 in categories_1:
        for cat_2 in categories_2:
            print_ln("Freq (%s, %s): %s", cat_1, cat_2, counts[cat_1][cat_2].reveal())


def xtabs_mode(flag, group_by, cat_len_1, cat_len_2):
    counts = Matrix(cat_len_1, cat_len_2, sint)    
    modes = Array(cat_len_1, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)
    eq_cat_2 = [(group_by.get_column(1) == j) * flag for j in categories_2] if flag else [(group_by.get_column(1) == j) for j in categories_2]

    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            counts[i][j] = (eq_cat_1 * eq_cat_2[j]).sum()
    
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
    print("Share type (if applicable):", compiler.options.share_type)
    print("Rows:", compiler.options.rows)
    print("Number of categories for first column:", compiler.options.n_cat_1)
    print("Number of categories for second column (if applicable):", compiler.options.n_cat_2)
    print("Aggregation type:", compiler.options.aggregation)
    print("Group by columns:", compiler.options.group_by)
    print("Value column (if applicable):", compiler.options.values)
    print("----------------------------------------------------------------")


@compiler.register_function(function_name)
def main():
    print_compiler_options()
    compiler.prog.use_trunc_pr = True
    stype_val = sfix if 'fix' in compiler.prog.args else sint
    num_group_by = len(compiler.options.group_by)
    fact = {
        'psi': PsiInput,
        'pid': PrivateIdInput,
        'cpsi': lambda: CircuitPsiInput(compiler.options.share_type),
        'ps3i': CrossPsiInput,
        'ps3i-xor': CrossPsiXorInput,
    }
    provider = fact[compiler.options.protocol]() 
    if num_group_by == 1:
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.group_by), sint)
        values = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.values), stype_val)
        xtabs_1(compiler.options.aggregation, flag, group_by, values, stype_val, compiler.options.n_cat_1)

    elif num_group_by == 2:
        alice_cols, bob_cols = parse_column_spec(compiler.options.group_by)
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_matrix(compiler.options.rows, alice_cols, bob_cols)
        values = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.values), stype_val) if compiler.options.values else None
        xtabs_2(compiler.options.aggregation, flag, group_by, values, stype_val, compiler.options.n_cat_1, compiler.options.n_cat_2)
    else:
        raise ValueError(f"Unsupported number of columns to group by: {num_group_by}")


if __name__ == "__main__":
    compiler.compile_func()