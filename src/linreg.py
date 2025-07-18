from Compiler.types import Array, Matrix, sfix
from Compiler.library import print_ln, for_range_opt, for_range, for_range_parallel
from Compiler.compilerLib import Compiler
from Compiler import ml
import re
#import torch.nn as nn

usage = "usage: %prog [options] [args]"
compiler = Compiler(usage=usage)

# Options for defining the input matrices and their dimensions
compiler.parser.add_option("--rows", dest="rows", type=int, help="Number of rows for the input matrices)")

# Options for defining X and y (The feature columns will all be taken as input at once and the label column must be the last column of the respective party)
compiler.parser.add_option("--features", dest="features", type=str, help="Feature columns (e.g a3b1 for Alice's first 3 columns and Bob's first column)")
compiler.parser.add_option("--label", dest="label", type=str, help="Label column (e.g b for Bob's column)")
compiler.parser.add_option("--test_size", dest="test_size", default=0.2, type=float, help="Proportion of the dataset to include in the test split (default: 0.2)")

# SGD options
compiler.parser.add_option("--n_epochs", dest="n_epochs", default=100, type=int, help="Number of epochs for SGD linear regression (default: 100)")
compiler.parser.add_option("--batch_size", dest="batch_size", default=1, type=int, help="Batch size for SGD linear regression (default: 1)")
compiler.parser.add_option("--learning_rate", dest="learning_rate", default=0.01, type=float, help="Learning rate for SGD linear regression (default: 0.01)")

compiler.parse_args()

if not compiler.options.rows:
    compiler.parser.error("--rows required")


def simple_linreg(max_rows):
    """
    Simple linreg where Alice holds the feature column and Bob holds the target column. Purely for demonstration purposes.
    """

    alice = Array(max_rows, sfix)
    bob = Array(max_rows, sfix)

    # Change precision to avoid overflows
    sfix.set_precision(16, 47)  # Might need to compile with -R 192.

    alice.input_from(0)
    bob.input_from(1)

    sum_x = sfix(0)
    sum_y = sfix(0)
    sum_xy = sfix(0)
    sum_x2 = sfix(0)

    @for_range_opt(max_rows)
    def _(i):
        sum_x.update(sum_x + alice[i])
        sum_y.update(sum_y + bob[i])
        sum_xy.update(sum_xy + alice[i] * bob[i])
        sum_x2.update(sum_x2 + alice[i] ** 2)

    beta_1 = (max_rows * sum_xy - sum_x * sum_y) / (max_rows * sum_x2 - sum_x * sum_x)
    beta_0 = (sum_y - beta_1 * sum_x) / max_rows

    #print_ln("Sum of X: %s", sum_x.reveal())
    #print_ln("Sum of Y: %s", sum_y.reveal())
    #print_ln("Sum of XY: %s", sum_xy.reveal())
    #print_ln("Sum of X^2: %s", sum_x2.reveal())

    print_ln("Intercept (beta_0): %s", beta_0.reveal())
    print_ln("Slope (beta_1): %s", beta_1.reveal())


def parse_columns(format_str):
    pattern = r"^a(\d*)b(\d*)$"
    
    # Match the pattern
    match = re.match(pattern, format_str)
    
    if match:
        a_str, b_str = match.groups()
        
        a_columns = int(a_str) if a_str else 0
        b_columns = int(b_str) if b_str else 0
        
        return a_columns, b_columns
    
    else:
        raise ValueError(f"Invalid format: {format_str}")
    

def get_X(alice_columns, bob_columns, rows_train, rows_test):
    num_features = alice_columns + bob_columns

    print(f"Number of features for Alice: {alice_columns}")
    print(f"Number of features for Bob: {bob_columns}")

    X_train = Matrix(rows_train, num_features, sfix)
    X_test = Matrix(rows_test, num_features, sfix)

    current_train_column = current_test_column = 0
    for _ in range(alice_columns):
        @for_range_opt(rows_train)
        def _(i):
            X_train[i][current_train_column] = sfix.get_input_from(0)
        
        current_train_column += 1

    for _ in range(bob_columns):
        @for_range_opt(rows_train)
        def _(i):
            X_train[i][current_train_column] = sfix.get_input_from(1)

        current_train_column += 1

    for _ in range(alice_columns):
        @for_range_opt(rows_test)
        def _(i):
            X_test[i][current_test_column] = sfix.get_input_from(0)

        current_test_column += 1

    for _ in range(bob_columns):
        @for_range_opt(rows_test)
        def _(i):
            X_test[i][current_test_column] = sfix.get_input_from(1)

        current_test_column += 1
    

    return X_train, X_test


def get_y(label, rows_train, rows_test):
    party = 0 if label == 'a' else 1

    y_train = Array(rows_train, sfix)
    y_test = Array(rows_test, sfix)

    y_train.input_from(party)
    y_test.input_from(party)

    return y_train, y_test


# To optimize memory usage, the features argument should specify the required columns from each party in ascending order so each column can be taken as input all at once and avoid
# storing an additional matrix for alice's and bob's values
def sgd_linreg(max_rows, features, label, test_size, n_epochs, batch_size, learning_rate):
    rows_train = int(max_rows * (1 - test_size))
    rows_test = int(max_rows * test_size)

    alice_columns, bob_columns = parse_columns(features)

    X_train, X_test = get_X(alice_columns, bob_columns, rows_train, rows_test)
    y_train, y_test = get_y(label, rows_train, rows_test)

    """ for i in range(X_train.shape[0]):
        for j in range(X_train.shape[1]):
            print_ln("X_train[%s][%s]: %s", i, j, X_train[i][j].reveal())

    for i in range(X_test.shape[0]):
        for j in range(X_test.shape[1]):
            print_ln("X_test[%s][%s]: %s", i, j, X_test[i][j].reveal()) """

    #print_ln("y_train: %s", y_train.reveal())
    #print_ln("y_test: %s", y_test.reveal())
    
    
    linear = ml.SGDLinear(n_epochs, batch_size)
    linear.fit(X_train, y_train)

    print_ln('Model Weights: %s', linear.opt.layers[0].W[:].reveal())
    print_ln('Model Bias: %s', linear.opt.layers[0].b.reveal())
    #print_ln('Diff: %s', (linear.predict(X_test) - y_test).reveal())
    # Thetas
    #for theta in linear.opt.thetas:
    #    print_ln('Theta: %s', theta.reveal())


    # Something like this that uses proper torch layers might be needed for implementing polyfeats and multivariate linreg
    # (https://mp-spdz.readthedocs.io/en/latest/machine-learning.html#pytorch-interface)
    # (https://mp-spdz.readthedocs.io/en/latest/machine-learning.html#keras-interface)
    """ net = nn.Sequential(
    nn.Flatten(),
    nn.Linear(28 * 28, 128),
    nn.ReLU(),
    nn.Linear(128, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
    )

    ml.set_n_threads(int(program.args[2]))

    layers = ml.layers_from_torch(net, training_samples.shape, 128)

    optimizer = ml.SGD(layers)
    optimizer.fit(
    training_samples,
    training_labels,
    epochs=int(program.args[1]),
    batch_size=128,
    validation_data=(test_samples, test_labels),
    program=program
    ) """


def print_compiler_options(compiler_message, sgd=True):
    print("----------------------------------------------------------------")
    print(compiler_message)
    print("----------------------------------------------------------------")
    print("Compiler options:")
    print("Rows:", compiler.options.rows)
    if sgd:
        print("Features:", compiler.options.features)
        print("Label:", compiler.options.label)
        print("Test size:", compiler.options.test_size)
        print("Number of epochs:", compiler.options.n_epochs)
        print("Batch size:", compiler.options.batch_size)
        print("Learning rate:", compiler.options.learning_rate)
    print("----------------------------------------------------------------")


@compiler.register_function('linreg')
def main():
    compiler.prog.use_trunc_pr = True # Comment this line if the protocol cannot use probabilistic truncation

    max_rows = compiler.options.rows

    if "simple" in compiler.prog.args:
        print_compiler_options("Compiling for simple linear regression", sgd=False)
        simple_linreg(max_rows)
        return
    
    features = compiler.options.features
    label = compiler.options.label
    if not features or not label:
        compiler.parser.error("--features and --label are required for sgd linear regression")
    test_size = compiler.options.test_size
    n_epochs = compiler.options.n_epochs
    batch_size = compiler.options.batch_size
    learning_rate = compiler.options.learning_rate

    print_compiler_options("Compiling for linear regression using SGD")
    sgd_linreg(max_rows, features, label, test_size, n_epochs, batch_size, learning_rate)
    

if __name__ == "__main__":
    compiler.compile_func()