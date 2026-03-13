from Compiler.library import print_ln
from Compiler.compilerLib import Compiler
from Compiler.mpc_math import sqrt
from Compiler.types import sint, sfix, Array, Matrix
from common.input import InputFactory
from common.utils import get_party_from_char, mux, parse_column_spec


usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)
input_factory = InputFactory(compiler)  # Adds necessary compiler options for input and provides method to create input module based on parsed options

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices")

# Program-specific compiler options
compiler.parser.add_option("--n_cat_1", dest="n_cat_1", default=4, type=int, help="Number of categories for the first aggregation column")
compiler.parser.add_option("--n_cat_2", dest="n_cat_2", default=4, type=int, help="Number of categories for the second aggregation column (if applicable)")
compiler.parser.add_option("--aggregation", dest="aggregation", type=str, help="Type of aggregation to be performed (sum, avg, freq, mode, std)")
compiler.parser.add_option("--group_by", dest="group_by", type=str, help="Columns to group by (2 max) (e.g ab for Alice's first column and Bob's first column)")
compiler.parser.add_option("--values", dest="values", type=str, help="Value column (not needed for mode and freq.) (e.g b for Bob's column)")

compiler.parse_args()

# Compiler checks
if not compiler.options.rows or not compiler.options.protocol:
    compiler.parser.error("--rows and --protocol required")


def xtabs_sum1(flag, group_by, values, cat_len):
    sums = Array(cat_len, values.value_type)
    sums.check

    values = values * flag if flag else values
    for i in range(cat_len):
        sums[i] = ((group_by == i) * values).sum()
    
    return sums


def xtabs_sum2(flag, group_by, values, cat_len_1, cat_len_2):
    sums = Matrix(cat_len_1, cat_len_2, values.value_type)

    values = values * flag if flag else values
    eq_cat_2 = [group_by.get_column(1) == j for j in range(cat_len_2)]
    for i in range(cat_len_1):
        eq_cat_1 = group_by.get_column(0) == i
        for j in range(cat_len_2):
            sums[i][j] = ((eq_cat_1 & eq_cat_2[j]) * values).sum()
    
    return sums


def xtabs_avg1(flag, group_by, values, cat_len):
    averages = Array(cat_len, sfix)
    group_by = group_by * flag if flag else group_by
    eq_cat = [(group_by == i) for i in range(1, cat_len + 1)]
    
    for i in range(cat_len):
        sum = (eq_cat[i] * values).sum()
        count = eq_cat[i].sum()
        averages[i] = sum / count

    return averages


def xtabs_avg2(flag, group_by, values, cat_len_1, cat_len_2):
    averages = Matrix(cat_len_1, cat_len_2, sfix)
    if flag:
        group_by.set_column(0, group_by.get_column(0) * flag)
    eq_cat_2 = [(group_by.get_column(1) == j) for j in range(1, cat_len_2 + 1)]

    for i in range(cat_len_1):
        eq_cat_1 = group_by.get_column(0) == i + 1
        for j in range(cat_len_2):
            full_match = eq_cat_1 * eq_cat_2[j]
            sum = (full_match * values).sum()
            count = full_match.sum()
            averages[i][j] = sum / count

    return averages


def xtabs_std1(flag, group_by, values, cat_len, ddof=0):
    stdevs = Array(cat_len, sfix)
    categories = range(cat_len)
    eq_cat = [(group_by == i) * flag for i in categories] if flag else [(group_by == i) for i in categories]

    for i in categories:
        sum = (eq_cat[i] * values).sum()
        count = eq_cat[i].sum()
        average = sum / count
        variance = (eq_cat[i] * (values - average)**2).sum()
        stdevs[i] = sqrt(variance / (count - ddof))
    
    return stdevs


def xtabs_std2(flag, group_by, values, cat_len_1, cat_len_2, ddof=0):
    stdevs = Matrix(cat_len_1, cat_len_2, sfix)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)  

    eq_cat_2 = [(group_by.get_column(1) == j) * flag for j in categories_2] if flag else [(group_by.get_column(1) == j) for j in categories_2]

    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            full_match = eq_cat_1 * eq_cat_2[j]
            sum = (full_match * values).sum()
            count = full_match.sum()
            average = sum / count
            variance = (full_match * (values - average)**2).sum()
            stdevs[i][j] = sqrt(variance / (count - ddof))

    return stdevs


def xtabs_freq(flag, group_by, cat_len_1, cat_len_2):
    counts = Matrix(cat_len_1, cat_len_2, sint)    
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)
    eq_cat_2 = [(group_by.get_column(1) == j) * flag for j in categories_2] if flag else [(group_by.get_column(1) == j) for j in categories_2]
    for i in categories_1:
        eq_cat_1 = group_by.get_column(0) == i
        for j in categories_2:
            counts[i][j] = (eq_cat_1 * eq_cat_2[j]).sum()
    
    return counts


def xtabs_mode(flag, group_by, cat_len_1, cat_len_2):  
    modes = Array(cat_len_1, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    counts = xtabs_freq(flag, group_by, cat_len_1, cat_len_2)   
    
    for cat_1 in categories_1:
        max_value = sint(0)
        mode = sint(-1)
        for cat_2 in categories_2:
            geq = counts[cat_1][cat_2] > max_value
            max_value = mux(geq, counts[cat_1][cat_2], max_value)
            eq_max = counts[cat_1][cat_2] == max_value
            mode = mux(eq_max, cat_2, mode)
        modes[cat_1] = mode

    return modes


def xtabs_1(aggregation, flag, group_by, values, cat_len):
    if aggregation == 'sum':
        return xtabs_sum1(flag, group_by, values, cat_len)
    elif aggregation == 'avg':
        return xtabs_avg1(flag, group_by, values, cat_len)
    elif aggregation == 'std':
        return xtabs_std1(flag, group_by, values, cat_len)
    elif aggregation == 'freq':
        raise ValueError("Frequency aggregation not supported for single column")
    elif aggregation == 'mode':
        raise ValueError("Mode aggregation not supported for single column")
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def xtabs_2(aggregation, flag, group_by, values, cat_len_1, cat_len_2):
    if aggregation == 'sum':
        return xtabs_sum2(flag, group_by, values, cat_len_1, cat_len_2)
    elif aggregation == 'avg':
        return xtabs_avg2(flag, group_by, values, cat_len_1, cat_len_2)
    elif aggregation == 'std':
        return xtabs_std2(flag, group_by, values, cat_len_1, cat_len_2)
    elif aggregation == 'freq':
        return xtabs_freq(flag, group_by, cat_len_1, cat_len_2)
    elif aggregation == 'mode':
        return xtabs_mode(flag, group_by, cat_len_1, cat_len_2)
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


@compiler.register_function(f"xtabs-{compiler.options.aggregation}-{len(compiler.options.group_by)}") # e.g. xtabs-sum-2
def main():
    print_compiler_options()
 
    compiler.prog.use_trunc_pr = True
    stype_val = sfix if 'fix' in compiler.prog.args else sint
    num_group_by = len(compiler.options.group_by)

    provider = input_factory.create_input()
    result = None
    if num_group_by == 1:
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.group_by), sint)
        values = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.values), stype_val)
        result = xtabs_1(compiler.options.aggregation, flag, group_by, values, compiler.options.n_cat_1)

    elif num_group_by == 2:
        alice_cols, bob_cols = parse_column_spec(compiler.options.group_by)
        flag = provider.get_flag(compiler.options.rows)
        group_by = provider.get_matrix(compiler.options.rows, alice_cols, bob_cols)
        values = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.values), stype_val) if compiler.options.values else None
        result = xtabs_2(compiler.options.aggregation, flag, group_by, values, compiler.options.n_cat_1, compiler.options.n_cat_2)
    else:
        raise ValueError(f"Unsupported number of columns to group by: {num_group_by}")
    
    result.print_reveal_nested()


if __name__ == "__main__":
    compiler.compile_func()