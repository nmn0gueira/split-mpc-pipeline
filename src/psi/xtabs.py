from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
from Compiler.mpc_math import sqrt
from Compiler.types import sint, cint, sfix, Array, Matrix

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices)")
compiler.parser.add_option("--n_cat_1", dest="n_cat_1", default=4, type=int, help="Number of categories for the first aggregation column")
compiler.parser.add_option("--n_cat_2", dest="n_cat_2", default=4, type=int, help="Number of categories for the second aggregation column (if applicable)")

compiler.parser.add_option("--aggregation", dest="aggregation", type=str, help="Type of aggregation to be performed (sum, avg, freq, mode, std")
compiler.parser.add_option("--group_by", dest="group_by", type=str, help="Columns to group by (2 max) (e.g ab for Alice's first column and Bob's first column")
compiler.parser.add_option("--value_col", dest="value_col", type=str, help="Value column (not needed for mode and freq.) (e.g b for Bob's column)")

compiler.parse_args()

if not compiler.options.rows:
    compiler.parser.error("--rows")

function_name = f"xtabs-{compiler.options.aggregation}-{len(compiler.options.group_by)}"    # e.g. xtabs-sum-2

def mux(cond, trueVal, falseVal):
    return cond.if_else(trueVal, falseVal)


def parse_cols(cols):
    alice_cols = bob_cols = 0
    for i in range(len(cols)):
        if cols[i] == 'a':
            alice_cols += 1
        elif cols[i] == 'b':
            bob_cols += 1
        else:
            raise ValueError(f"Unexpected column format: {cols}")
    return alice_cols, bob_cols


def get_array(rows, party, secret_type):
    party = 0 if party == 'a' else 1
    array = Array(rows, secret_type)
    array.input_from(party)

    return array


def get_matrix(rows, cols, secret_type):
    alice_cols, bob_cols = parse_cols(cols)

    matrix = Matrix(rows, len(cols), secret_type)
    current_column = 0
    for _ in range(alice_cols):
        @for_range_opt(rows)
        def _(i):
            matrix[i][current_column] = secret_type.get_input_from(0)
        current_column += 1

    for _ in range(bob_cols):
        @for_range_opt(rows)
        def _(i):
            matrix[i][current_column] = secret_type.get_input_from(1)
        current_column += 1
    
    return matrix


def xtabs_sum1(max_rows, group_by, value_col, stype_val, cat_len):
    group_by_col = get_array(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    categories = range(cat_len)

    @for_range_opt(max_rows)
    def _(i):
        for category in categories:
            sums[category] += (group_by_col[i] == category) * values[i]

    
    for category in categories:
        print_ln("Sum %s: %s", category, sums[category].reveal())


def xtabs_sum2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                sums[category_1][category_2] += (match_1 & (group_by_cols[i][1] == category_2)) * values[i]

    
    for category_1 in categories_1:
        for category_2 in categories_2:
            print_ln("Sum (%s, %s): %s", category_1, category_2, sums[category_1][category_2].reveal())


def xtabs_avg1(max_rows, group_by, value_col, stype_val, cat_len):
    group_by_col = get_array(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    categories = range(cat_len)
    
    @for_range_opt(max_rows)
    def _(i):
        for category in categories:
            full_match = group_by_col[i] == category
            sums[category] += full_match * values[i]
            counts[category] += full_match

    
    for category in categories:
        print_ln("Avg %s: %s", category, (sums[category] / counts[category]).reveal())


def xtabs_avg2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                full_match = match_1 & (group_by_cols[i][1] == category_2)
                sums[category_1][category_2] += full_match * values[i]
                counts[category_1][category_2] += full_match

    
    for category_1 in categories_1:
        for category_2 in categories_2:
            print_ln("Avg (%s, %s): %s", category_1, category_2, (sums[category_1][category_2] / counts[category_1][category_2]).reveal())


def xtabs_std1(max_rows, group_by, value_col, stype_val, cat_len, ddof=0):
    group_by_col = get_array(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, sint)
    categories = range(cat_len)
    averages = Array(cat_len, sfix)
    variances = Array(cat_len, sfix)

    @for_range_opt(max_rows)
    def _(i):
        for category in categories:
            full_match = group_by_col[i] == category
            sums[category] += full_match * values[i]
            counts[category] += full_match
    
    for category in categories:
        averages[category] = sums[category] / counts[category]

    @for_range_opt(max_rows)
    def _(i):
        for category in categories:
            variances[category] += (group_by_col[i] == category) * ((values[i] - averages[category]) ** 2)


    for category in categories:
        print_ln("Std %s: %s", category, sqrt(variances[category] / (counts[category] - ddof)).reveal())


def xtabs_std2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2, ddof=0):
    group_by_cols = get_matrix(max_rows, group_by, sint)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)  
    averages = Matrix(cat_len_1, cat_len_2, sfix)
    variances = Matrix(cat_len_1, cat_len_2, sfix)

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                full_match = match_1 & (group_by_cols[i][1] == category_2)
                sums[category_1][category_2] += full_match * values[i]
                counts[category_1][category_2] += full_match

    for category_1 in categories_1:
        for category_2 in categories_2:
            averages[category_1][category_2] = sums[category_1][category_2] / counts[category_1][category_2]

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                variances[category_1][category_2] += (match_1 & (group_by_cols[i][1] == category_2)) * ((values[i] - averages[category_1][category_2]) ** 2)
    

    for category_1 in categories_1:
        for category_2 in categories_2:
            print_ln("Std (%s, %s): %s", category_1, category_2, sqrt(variances[category_1][category_2] / (counts[category_1][category_2] - ddof)).reveal())


def xtabs_freq(max_rows, group_by, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, sint)

    counts = Matrix(cat_len_1, cat_len_2, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                counts[category_1][category_2] += match_1 & (group_by_cols[i][1] == category_2)

    
    for category_1 in categories_1:
        for category_2 in categories_2:
            print_ln("Freq (%s, %s): %s", category_1, category_2, counts[category_1][category_2].reveal())


def xtabs_mode(max_rows, group_by, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, sint)

    counts = Matrix(cat_len_1, cat_len_2, sint)
    modes = Array(cat_len_1, sint)
    categories_1 = range(cat_len_1)
    categories_2 = range(cat_len_2)

    @for_range_opt(max_rows)
    def _(i):
        for category_1 in categories_1:
            match_1 = group_by_cols[i][0] == category_1
            for category_2 in categories_2:
                counts[category_1][category_2] += match_1 & (group_by_cols[i][1] == category_2)

    
    for category_1 in categories_1:
        max_value = sint(0)
        mode = sint(-1)
        for category_2 in categories_2:
            geq = counts[category_1][category_2] > max_value
            max_value = mux(geq, counts[category_1][category_2], max_value)
            eq_max = counts[category_1][category_2] == max_value
            mode = mux(eq_max, category_2, mode)
        modes[category_1] = mode

    for category_1 in categories_1:
        print_ln("Mode %s: %s", category_1, modes[category_1].reveal())


def xtabs_1(aggregation, max_rows, group_by, value_col, stype_val, cat_len):
    if aggregation == 'sum':
        xtabs_sum1(max_rows, group_by, value_col, stype_val, cat_len)
    elif aggregation == 'avg':
        xtabs_avg1(max_rows, group_by, value_col, stype_val, cat_len)
    elif aggregation == 'std':
        xtabs_std1(max_rows, group_by, value_col, stype_val, cat_len)
    elif aggregation == 'freq':
        raise ValueError("Frequency aggregation not supported for single column")
    elif aggregation == 'mode':
        raise ValueError("Mode aggregation not supported for single column")
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def xtabs_2(aggregation, max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2):
    if aggregation == 'sum':
        xtabs_sum2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'avg':
        xtabs_avg2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'std':
        xtabs_std2(max_rows, group_by, value_col, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'freq':
        xtabs_freq(max_rows, group_by, cat_len_1, cat_len_2)
    elif aggregation == 'mode':
        xtabs_mode(max_rows, group_by, cat_len_1, cat_len_2)
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def print_compiler_options(compiler_message):
    print("----------------------------------------------------------------")
    print(compiler_message)
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Rows:", compiler.options.rows)
    print("Number of categories for first column:", compiler.options.n_cat_1)
    print("Number of categories for second column (if applicable):", compiler.options.n_cat_2)
    print("Aggregation type:", compiler.options.aggregation)
    print("Group by columns:", compiler.options.group_by)
    print("Value column (if applicable):", compiler.options.value_col)
    print("----------------------------------------------------------------")


@compiler.register_function(function_name)
def main():
    max_rows = compiler.options.rows
    n_categories_1 = compiler.options.n_cat_1
    n_categories_2 = compiler.options.n_cat_2
    aggregation = compiler.options.aggregation
    group_by = compiler.options.group_by
    value_col = compiler.options.value_col
    num_group_by = len(group_by)

    compiler.prog.use_trunc_pr = True # Comment this line if the protocol cannot use probabilistic truncation
    #sfix.round_nearest= True
    stype_val = sfix if 'fix' in compiler.prog.args else sint

    print_compiler_options(f"Compiling for arithmetic circuits with {stype_val} secret type")

    if num_group_by == 1:
        xtabs_1(aggregation, max_rows, group_by, value_col, stype_val, n_categories_1)

    elif num_group_by == 2:
        xtabs_2(aggregation, max_rows, group_by, value_col, stype_val, n_categories_1, n_categories_2)
    else:
        raise ValueError(f"Unsupported number of columns to group by: {num_group_by}")


if __name__ == "__main__":
    compiler.compile_func()