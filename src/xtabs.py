from Compiler.library import print_ln, for_range_opt
from Compiler.compilerLib import Compiler
from Compiler.mpc_math import sqrt
from Compiler.types import sint, cint, sfix, Array, Matrix
from Compiler.GC.types import sbitintvec, sbitfixvec
from Compiler.oram import OptimalORAM

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices)")
compiler.parser.add_option("--n_cat_1", dest="n_cat_1", default=4, type=int, help="Number of categories for the first aggregation column")
compiler.parser.add_option("--n_cat_2", dest="n_cat_2", default=4, type=int, help="Number of categories for the second aggregation column (if applicable)")

compiler.parser.add_option("--aggregation", dest="aggregation", type=str, help="Type of aggregation to be performed (sum, average, freq(uencies), st(d)ev)")
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



def xtabs_sum1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len):
    group_by_col = get_array(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    categories = Array(cat_len, ctype)

    for i in range(cat_len):
        sums[i] = stype_val(0)
        categories[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len):
            sums[j] += mux(group_by_col[i] == categories[j], values[i], 0)

    
    for i in range(cat_len):
        print_ln("Sum %s: %s", i, sums[i].reveal())


def xtabs_sum2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    categories_1 = Array(cat_len_1, ctype)
    categories_2 = Array(cat_len_2, ctype)

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            sums[i] = stype_val(0)

    for i in range(cat_len_1):
        categories_1[i] = ctype(i)

    for i in range(cat_len_2):
        categories_2[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                sums[j][k] += mux(match_1 & (group_by_cols[i][1] == categories_2[k]), values[i], 0)


    
    for i in range(cat_len_1):
        for j in range(cat_len_2):
            print_ln("Sum (%s, %s): %s", i, j, sums[i][j].reveal())


def xtabs_avg1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len):
    group_by_col = get_array(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, stype_cmp)  # Counts are always going to be the same as the secret type used for comparisons (which only depends on the computation domain)
    categories = Array(cat_len, ctype)

    for i in range(cat_len):
        sums[i] = stype_val(0)
        counts[i] = stype_cmp(0)
        categories[i] = ctype(i)

    
    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len):
            full_match = group_by_col[i] == categories[j]
            sums[j] += mux(full_match, values[i], 0)
            counts[j] += full_match

    
    for i in range(cat_len):
        print_ln("Avg %s: %s", i, (sums[i] / counts[i]).reveal())


def xtabs_avg2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, stype_cmp)  # Counts are always going to be the same as the secret type used for comparisons (which only depends on the computation domain)
    categories_1 = Array(cat_len_1, ctype)
    categories_2 = Array(cat_len_2, ctype)

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            sums[i][j] = stype_val(0)
            counts[i][j] = stype_cmp(0)

    for i in range(cat_len_1):
        categories_1[i] = ctype(i)

    for i in range(cat_len_2):
        categories_2[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                full_match = match_1 & (group_by_cols[i][1] == categories_2[k])
                sums[j][k] += mux(full_match, values[i], 0)
                counts[j][k] += full_match

    
    for i in range(cat_len_1):
        for j in range(cat_len_2):
            print_ln("Avg (%s, %s): %s", i, j, (sums[i][j] / counts[i][j]).reveal())


def xtabs_std1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len, ddof=0):
    group_by_col = get_array(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Array(cat_len, stype_val)
    counts = Array(cat_len, stype_cmp)
    categories = Array(cat_len, ctype)
    # For now this is like this since this aggregation will only work in arithmetic circuits anyway
    averages = Array(cat_len, sfix)
    variances = Array(cat_len, sfix)

    for i in range(cat_len):
        sums[i] = stype_val(0)
        counts[i] = stype_cmp(0)
        categories[i] = ctype(i)
        variances[i] = sfix(0)


    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len):
            full_match = group_by_col[i] == categories[j]
            sums[j] += mux(full_match, values[i], 0)
            counts[j] += full_match

    
    for i in range(cat_len):
        averages[i] = sums[i] / counts[i]

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len):
            variances[j] += mux(group_by_col[i] == categories[j], (values[i] - averages[j]) ** 2, 0)


    for i in range(cat_len):
        print_ln("Std %s: %s", i, sqrt(variances[i] / (counts[i] - ddof)).reveal())


def xtabs_std2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2, ddof=0):
    group_by_cols = get_matrix(max_rows, group_by, stype_cmp)
    values = get_array(max_rows, value_col, stype_val)

    sums = Matrix(cat_len_1, cat_len_2, stype_val)
    counts = Matrix(cat_len_1, cat_len_2, stype_cmp)  # Counts are always going to be the same as the secret type used for comparisons (which only depends on the computation domain)
    categories_1 = Array(cat_len_1, ctype)
    categories_2 = Array(cat_len_2, ctype)   
    # For now this is like this since this aggregation will only work in arithmetic circuits anyway
    averages = Matrix(cat_len_1, cat_len_2, sfix)
    variances = Matrix(cat_len_1, cat_len_2, sfix)

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            sums[i][j] = stype_val(0)
            counts[i][j] = stype_cmp(0)
            variances[i][j] = sfix(0)

    for i in range(cat_len_1):
        categories_1[i] = ctype(i)

    for i in range(cat_len_2):
        categories_2[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                full_match = match_1 & (group_by_cols[i][1] == categories_2[k])
                sums[j][k] += mux(full_match, values[i], 0)
                counts[j][k] += full_match
    

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            averages[i][j] = sums[i][j] / counts[i][j]


    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                variances[j][k] += mux(match_1 & (group_by_cols[i][1] == categories_2[k]), (values[i] - averages[j][k]) ** 2, 0)
    

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            print_ln("Std %s: %s", i, sqrt(variances[i][j] / (counts[i][j] - ddof)).reveal())


def xtabs_freq(max_rows, group_by, ctype, stype_cmp, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, stype_cmp)

    counts = Matrix(cat_len_1, cat_len_2, stype_cmp)  # Counts are always going to be the same as the secret type used for comparisons (which only depends on the computation domain)
    categories_1 = Array(cat_len_1, ctype)
    categories_2 = Array(cat_len_2, ctype)

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            counts[i][j] = stype_cmp(0)

    for i in range(cat_len_1):
        categories_1[i] = ctype(i)

    for i in range(cat_len_2):
        categories_2[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                counts[j][k] += match_1 & (group_by_cols[i][1] == categories_2[k])

    
    for i in range(cat_len_1):
        for j in range(cat_len_2):
            print_ln("Freq (%s, %s): %s", i, j, counts[i][j].reveal())


def xtabs_mode(max_rows, group_by, ctype, stype_cmp, cat_len_1, cat_len_2):
    group_by_cols = get_matrix(max_rows, group_by, stype_cmp)

    counts = Matrix(cat_len_1, cat_len_2, stype_cmp)  # Counts are always going to be the same as the secret type used for comparisons (which only depends on the computation domain)
    modes = Array(cat_len_1, stype_cmp)
    categories_1 = Array(cat_len_1, ctype)
    categories_2 = Array(cat_len_2, ctype)

    for i in range(cat_len_1):
        for j in range(cat_len_2):
            counts[i][j] = stype_cmp(0)

    for i in range(cat_len_1):
        categories_1[i] = ctype(i)

    for i in range(cat_len_2):
        categories_2[i] = ctype(i)

    @for_range_opt(max_rows)
    def _(i):
        for j in range(cat_len_1):
            match_1 = group_by_cols[i][0] == categories_1[j]
            for k in range(cat_len_2):
                counts[j][k] += match_1 & (group_by_cols[i][1] == categories_2[k])

    
    for i in range(cat_len_1):
        max_value = stype_cmp(0)
        mode = stype_cmp(-1)
        for j in range(cat_len_2):
            geq = counts[i][j] > max_value
            max_value = mux(geq, counts[i][j], max_value)
            eq_max = counts[i][j] == max_value
            mode = mux(eq_max, categories_2[j], mode)
        modes[i] = mode

    for i in range(cat_len_1):
        print_ln("Mode %s: %s", i, modes[i].reveal())


def xtabs_1(aggregation, max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len):
    if aggregation == 'sum':
        xtabs_sum1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len)
    elif aggregation == 'avg':
        xtabs_avg1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len)
    elif aggregation == 'std':
        xtabs_std1(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len)
    elif aggregation == 'freq':
        raise ValueError("Frequency aggregation not supported for single column")
    elif aggregation == 'mode':
        raise ValueError("Mode aggregation not supported for single column")
    else:
        raise ValueError(f"Unsupported aggregation type: {aggregation}")


def xtabs_2(aggregation, max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2):
    if aggregation == 'sum':
        xtabs_sum2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'avg':
        xtabs_avg2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'std':
        xtabs_std2(max_rows, group_by, value_col, ctype, stype_cmp, stype_val, cat_len_1, cat_len_2)
    elif aggregation == 'freq':
        xtabs_freq(max_rows, group_by, ctype, stype_cmp, cat_len_1, cat_len_2)
    elif aggregation == 'mode':
        xtabs_mode(max_rows, group_by, ctype, stype_cmp, cat_len_1, cat_len_2)
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

    ctype = None
    stype_cmp = None
    stype_val = None
    compiler_message = None

    fixed = 'fix' in compiler.prog.args

    if compiler.prog.options.binary != 0: # If program is being compiled for binary circuits
        ctype = sbitintvec.get_type(int(compiler.prog.options.binary)) # In binary circuits there is no useful clear type for our purposes
        stype_cmp = ctype
        stype_val = sbitfixvec if fixed else stype_cmp
        compiler_message = f"Compiling for binary circuits with {stype_val} secret type"

    else:
        compiler.prog.use_trunc_pr = True # Comment this line if the protocol cannot use probabilistic truncation
        #sfix.round_nearest= True
        ctype = cint
        stype_cmp = sint
        stype_val = sfix if fixed else sint
        compiler_message = f"Compiling for arithmetic circuits with {stype_val} secret type"

    print_compiler_options(compiler_message)

    if num_group_by == 1:
        xtabs_1(aggregation, max_rows, group_by, value_col, ctype, stype_cmp, stype_val, n_categories_1)

    elif num_group_by == 2:
        xtabs_2(aggregation, max_rows, group_by, value_col, ctype, stype_cmp, stype_val, n_categories_1, n_categories_2)
    else:
        raise ValueError(f"Unsupported number of columns to group by: {num_group_by}")


if __name__ == "__main__":
    compiler.compile_func()