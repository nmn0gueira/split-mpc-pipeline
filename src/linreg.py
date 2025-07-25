from Compiler.types import Array, Matrix, sfix
from Compiler.library import print_ln
from Compiler.compilerLib import Compiler
from Compiler import ml
import re

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

compiler.parser.add_option("--n_threads", dest="n_threads", type=int, default=1, help="Number of threads to use for parallel execution")

compiler.parser.add_option("--protocol", dest="protocol", type=str, help="one of psi, cpsi, ps3i, ps3i-xor, pid")
compiler.parser.add_option("--share-type", dest="share_type", type=str, default="xor", help="for cpsi: xor or add32")

compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices")
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
        
        a_columns = int(a_str) if a_str else 0
        b_columns = int(b_str) if b_str else 0
        
        return a_columns, b_columns
    
    else:
        raise ValueError(f"Invalid format: {format_str}")
    

def load_feature_matrix(alice_columns, bob_columns, train_rows, test_rows):
    num_features = alice_columns + bob_columns
    print(f"Number of features for Alice: {alice_columns}")
    print(f"Number of features for Bob: {bob_columns}")
    X_train = Matrix(train_rows, num_features, sfix)
    X_test = Matrix(test_rows, num_features, sfix)
    for i in range(alice_columns):
        X_train.set_column(i, sfix.get_input_from(0, size=train_rows))
        X_test.set_column(i, sfix.get_input_from(0, size=test_rows)) 
    for i in range(bob_columns):
        X_train.set_column(alice_columns + i, sfix.get_input_from(1, size=train_rows))
        X_test.set_column(alice_columns + i, sfix.get_input_from(1, size=test_rows)) 

    return X_train, X_test


def load_label_vector(label_owner, train_rows, test_rows):
    party = 0 if label_owner == 'a' else 1
    y_train = Array(train_rows, sfix)
    y_test = Array(test_rows, sfix)
    y_train.input_from(party)
    y_test.input_from(party)
    return y_train, y_test


def mean_squared_error(y_true, y_pred):
    mse = sfix(0)
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
    X_train, X_test = load_feature_matrix(alice_columns, bob_columns, rows_train, rows_test)
    y_train, y_test = load_label_vector(compiler.options.label_owner, rows_train, rows_test)
    
    linear = ml.SGDLinear(compiler.options.n_epochs, compiler.options.batch_size)
    linear.fit(X_train, y_train)
    print_ln('Model Weights: %s', linear.opt.layers[0].W[:].reveal())
    print_ln('Model Bias: %s', linear.opt.layers[0].b.reveal())

    if 'mse' in compiler.prog.args:
        y_pred = linear.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print_ln('Mean Squared Error on Test Set: %s', mse.reveal())
    

if __name__ == "__main__":
    compiler.compile_func()