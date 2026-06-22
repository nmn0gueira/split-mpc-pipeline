from Compiler.types import sfix
from Compiler.library import print_ln
from Compiler.compilerLib import Compiler
from Compiler import ml
from common.input import InputFactory
from common.utils import get_party_from_char
import re

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)
input_factory = InputFactory(compiler)

compiler.parser.add_option("--n_threads", dest="n_threads", type=int, default=1, help="Number of threads to use for parallel execution")
compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices")

# Program-specific options
compiler.parser.add_option("--features", dest="feature_spec", type=str, help="Feature columns (e.g a3b1 for Alice's first 3 columns and Bob's first column)")
compiler.parser.add_option("--label", dest="label_owner", type=str, help="Label column (e.g b for Bob's column)")
compiler.parser.add_option("--test_size", dest="test_size", default=0.2, type=float, help="Proportion of the dataset to include in the test split (default: 0.2)")

compiler.parser.add_option("--n_epochs", dest="n_epochs", default=100, type=int, help="Number of epochs for SGD linear regression (default: 100)")
compiler.parser.add_option("--batch_size", dest="batch_size", default=1, type=int, help="Batch size for SGD linear regression (default: 1)")
compiler.parser.add_option("--learning_rate", dest="learning_rate", default=0.01, type=float, help="Learning rate for SGD linear regression (default: 0.01)")

compiler.parse_args()

if not compiler.options.rows or not compiler.options.feature_spec or not compiler.options.label_owner:
    compiler.parser.error("--rows, --features and --label are required")


def parse_feature_spec(format_str):
    pattern = r"^a(\d*)b(\d*)$"
    match = re.match(pattern, format_str)
    if match:
        a_str, b_str = match.groups()
        return int(a_str) if a_str else 0, int(b_str) if b_str else 0
    raise ValueError(f"Invalid format: {format_str}")


def mean_squared_error(y_true, y_pred, flag):
    mse = sfix(0)
    if flag:
        for i in range(y_true.shape[0]):
            mse += flag[i] * (y_true[i] - y_pred[i]) ** 2
    else:
        for i in range(y_true.shape[0]):
            mse += (y_true[i] - y_pred[i]) ** 2
    return mse / y_true.shape[0]


def print_compiler_options():
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Protocol:", compiler.options.protocol)
    print("Share type (if applicable):", compiler.options.share_type)
    print("Number of threads:", compiler.options.n_threads)
    print("Rows:", compiler.options.rows)
    print("Features:", compiler.options.feature_spec)
    print("Label:", compiler.options.label_owner)
    print("Test size:", compiler.options.test_size)
    print("Number of epochs:", compiler.options.n_epochs)
    print("Batch size:", compiler.options.batch_size)
    print("Learning rate:", compiler.options.learning_rate)
    print("----------------------------------------------------------------")


@compiler.register_function('linreg')
def main():
    print_compiler_options()
    ml.set_n_threads(int(compiler.options.n_threads))
    compiler.prog.use_trunc_pr = True

    rows_train = round(compiler.options.rows * (1 - compiler.options.test_size))
    rows_test = round(compiler.options.rows * compiler.options.test_size)
    alice_columns, bob_columns = parse_feature_spec(compiler.options.feature_spec)

    provider = input_factory.create_input()
    flag = provider.get_flag(compiler.options.rows)
    X = provider.get_matrix(compiler.options.rows, alice_columns, bob_columns, sfix)
    y = provider.get_array(compiler.options.rows, get_party_from_char(compiler.options.label_owner), sfix)

    linear = ml.SGDLinear(compiler.options.n_epochs, compiler.options.batch_size)
    linear.fit(X.get_part(0, rows_train), y.get_part(0, rows_train), sample_mask=flag.get_part(0, rows_train) if flag else None)
    print_ln('Model Weights: %s', linear.opt.layers[0].W[:].reveal())
    print_ln('Model Bias: %s', linear.opt.layers[0].b.reveal())

    if 'mse' in compiler.prog.args:
        if rows_test <= 0:
            raise ValueError("Cannot calculate mse without test dataset. Compile with an appropriate test size.")
        y_pred = linear.predict(X.get_part(rows_train, rows_test))
        mse = mean_squared_error(y.get_part(rows_train, rows_test), y_pred, flag.get_part(rows_train, rows_test) if flag else None)
        print_ln('Mean Squared Error on Test Set: %s', mse.reveal())


if __name__ == "__main__":
    compiler.compile_func()
