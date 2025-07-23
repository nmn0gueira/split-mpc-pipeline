import argparse, random, os, math, errno
import numpy as np
import pandas as pd
from operator import itemgetter
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

np.set_printoptions(legacy='1.25')

BASE_DIR = "data/"
PARTY_ALICE = "alice"
PARTY_BOB = "bob"
PARTY_PUBLIC = "public"

def create_dirs(program):
    dirname = BASE_DIR + program + "/"
    alice_dir = dirname + PARTY_ALICE
    bob_dir = dirname + PARTY_BOB
    public_dir = dirname + PARTY_PUBLIC
    if not os.path.exists(alice_dir) or not os.path.exists(bob_dir) or not os.path.exists(public_dir):
        try:
            os.makedirs(alice_dir)
            os.makedirs(bob_dir)
            os.makedirs(public_dir)
        except OSError as e:
            if e.errno != errno.EEXIST: raise


def write_to_csv(program, party, *columns):
    filepath = os.path.join(BASE_DIR, program, party, "data.csv")
    data = {}
    if isinstance(columns[0], (list, np.ndarray)):
        for i, column in enumerate(columns):
            data["col" + str(i)] = column
    else:
        data["col0"] = columns

    pd.DataFrame(data).to_csv(filepath, index=False, header=False)


def get_rand_list(bits, l):
    return [random.getrandbits(bits) for _ in range(l)]


def gen_input(n_bits, l):
    if (n_bits > 32):
        raise ValueError("invalid bit length---this test can only handle up to 32 bits")

    bits = int((n_bits - int(math.log(l, 2))) / 2)  # Ensure number of bits avoids overflow for large l
    
    list_a = get_rand_list(bits, l)
    list_b = get_rand_list(bits, l)
    
    return list_a, list_b

def get_ids(l, intersection_size):
    ids_a = []
    ids_b = []

    for i in range(l):
        id_a = 'user' + str(i + 1)

        id_b = 'user' + str(l + i + 1)
        if np.random.rand() < intersection_size:
            id_b = id_a

        ids_a.append(id_a)
        ids_b.append(id_b)

    return ids_a, ids_b



def gen_xtabs_input(l, intersection_size, n_categories_a, n_categories_b):
    '''
    Generates input for xtabs program. This input functions as if both parties already have their input ordered. One party has the (typically 
    categorical) value to group by (e.g. education level) and the other has the (typically continuous) values to aggregate upon (e.g. salary). The 
    output will depend on the function that is used to aggregate the values.
    '''
    NUM_CATEGORIES_DEFAULT = 4
    if n_categories_a is None:
        n_categories_a = NUM_CATEGORIES_DEFAULT
    if n_categories_b is None:
        n_categories_b = n_categories_a

    ids_a, ids_b = get_ids(l, intersection_size)
    categories_a, categories_b = [random.randrange(n_categories_a) for _ in range(l)], [random.randrange(n_categories_b) for _ in range(l)]
    values_a, values_b = gen_input(32, l)

    print_xtabs(ids_a, ids_b, categories_a, categories_b, values_b)
    return (ids_a, categories_a, values_a), (ids_b, categories_b, values_b)


def print_xtabs(ids_a, ids_b, categories_a, categories_b, values):
    input_len = len(categories_a)

    # Sums and averages
    sums = {}
    averages = {}
    counts = {}

    # Frequency counts
    frequencies = {}    # absolute frequencies
    modes = {}

    # Std
    std_values = {}
    std0 = {}   # ddof=0
    std1 = {}   # ddof=1

    for i in range(input_len):
        if ids_a[i] == ids_b[i]:
            sums[categories_a[i]] = sums.get(categories_a[i], 0) + values[i]
            counts[categories_a[i]] = counts.get(categories_a[i], 0) + 1
            std_values[categories_a[i]] = std_values.get(categories_a[i], [])
            std_values[categories_a[i]].append(values[i])

            frequency_dict = frequencies.get(categories_a[i], {})
            frequency_dict[categories_b[i]] = frequency_dict.get(categories_b[i], 0) + 1
            frequencies[categories_a[i]] = frequency_dict

    # Calculate averages
    for key in sums:
        averages[key] = sums[key] / counts[key]
    
    for key in std_values:
        #d2_sum = 0
        #for value in std_values[key]:
        #    d2 = abs(value - averages[key]) ** 2
        #    d2_sum += d2
        #var0 = d2_sum / counts[key]
        #var1 = d2_sum / (counts[key] - 1)
        #std0[key] = var0**0.5
        #std1[key] = var1**0.5
        #print(std0[key])
        #print(np.std(std_values[key], mean=averages[key]))
        #print(std1[key])
        #print(np.std(std_values[key], mean=averages[key], ddof=1))
        std0[key] = np.std(std_values[key], mean=averages[key])
        std1[key] = np.std(std_values[key], mean=averages[key], ddof=1) if len(std_values[key]) > 1 else None

        
    for k, v in frequencies.items():
        modes[k] = max(v.items(), key=itemgetter(1))[0]
        frequencies[k] = dict(sorted(frequencies[k].items()))   # Also sort the frequencies for better readability

    
    print("Grouping by column in a and aggregating on value column b:")
    print(f"Expected values (sum): {sorted(sums.items())}\n")
    print(f"Expected values (avg): {sorted(averages.items())}\n")
    print(f"Expected values (std0): {sorted(std0.items())}\n")
    print(f"Expected values (std1): {sorted(std1.items())}\n")

    print("-----------------------------------------------------------------------")
    print("Grouping by column in a and b (no value column):")
    print(f"Expected values (mode): {sorted(modes.items())}\n")
    print(f"Expected values (frequencies): {sorted(frequencies.items())}\n")

    print("-----------------------------------------------------------------------")

    sums = {}
    averages = {}

    std_values = {}
    std0 = {}   # ddof=0
    std1 = {}   # ddof=1
    
    for i in range(input_len):
        if ids_a[i] == ids_b[i]:
            sum_dict = sums.get(categories_a[i], {})
            sum_dict[categories_b[i]] = sum_dict.get(categories_b[i], 0) + values[i]
            sums[categories_a[i]] = sum_dict

            value_dict = std_values.get(categories_a[i], {})
            value_dict[categories_b[i]] = value_dict.get(categories_b[i], [])
            value_dict[categories_b[i]].append(values[i])
            std_values[categories_a[i]] = value_dict

    # Divide by each time a category combo appeared
    for key in sums:
        averages[key] = {}  # Create dictionary
        for k in sums[key]:
            averages[key][k] = sums[key][k] / frequencies[key][k]


    for key in std_values:
        std0[key] = {}
        std1[key] = {}
        for k in std_values[key]:
            std0[key][k] = np.std(std_values[key][k], mean=averages[key][k])
            std1[key][k] = np.std(std_values[key][k], mean=averages[key][k], ddof=1) if len(std_values[key][k]) > 1 else None
    
    for k, v in sums.items():
        sums[k] = dict(sorted(sums[k].items()))
        averages[k] = dict(sorted(averages[k].items())) 
        std0[k] = dict(sorted(std0[k].items()))
        std1[k] = dict(sorted(std1[k].items()))

    print("Grouping by column in a and b and aggregating on value column b:")
    print(f"Expected values (sum): {sorted(sums.items())}\n")
    print(f"Expected values (avg): {sorted(averages.items())}\n")
    print(f"Expected values (std0): {sorted(std0.items())}\n")
    print(f"Expected values (std1): {sorted(std1.items())}\n")


def gen_linreg_input(l, intersection_size, n_features, n_labels, scale_features=True, normalize_labels=True):
    NUM_FEATURES_DEFAULT = 1
    NUM_LABELS_DEFAULT = 1

    if n_features is None:
        n_features = NUM_FEATURES_DEFAULT
    if n_labels is None:
        n_labels = NUM_LABELS_DEFAULT
    
    X, Y = make_regression(n_samples=l, n_features=n_features, n_targets=n_labels)

    Y = Y.reshape(-1, n_labels)  # Ensure y is a 2D array with shape (l, n_labels)

    if scale_features:
        X = get_scaled(X)

    if normalize_labels:
        Y = get_normalized(Y)

    ids_a, ids_b = get_ids(l, intersection_size)
    X = np.hstack((np.array(ids_a).reshape(-1, 1), X))
    Y = np.hstack((np.array(ids_b).reshape(-1, 1), Y))

    print_linreg(X, Y)
    return X.transpose(), Y.transpose()


def get_scaled(features):
    mean = np.mean(features, axis=0)
    std = np.std(features, axis=0)
    scaled_features = (features - mean) / std
    return scaled_features


def get_normalized(labels):
    max_label = np.max(labels, axis=0)
    normalized_labels = labels / max_label
    return normalized_labels


def print_linreg(X, Y):
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    sample_weights_train = [1 if X_train[i, 0] == Y_train[i, 0] else 0 for i in range(len(X_train))]
    sample_weights_test = [1 if X_test[i, 0] == Y_test[i, 0] else 0 for i in range(len(X_test))]
    
    # Remove ids column from X_train and Y_train
    X_train = np.array(X_train[:, 1:], dtype=np.float64)
    X_test = np.array(X_test[:, 1:], dtype=np.float64)
    Y_train = np.array(Y_train[:, 1:], dtype=np.float64)
    Y_test = np.array(Y_test[:, 1:], dtype=np.float64)

    model = LinearRegression()
    model.fit(X_train, Y_train, sample_weight=sample_weights_train)
    print("Expected weights (w):\n", model.coef_)
    print("Expected intercept:\n", model.intercept_)
    print("Expected test error of model (MSE):", mean_squared_error(Y_test, model.predict(X_test), sample_weight=sample_weights_test))



def gen_hist2d_input(l, intersection_size, n_bins_x, n_bins_y):
    NUM_BINS_DEFAULT = 5
    if n_bins_x is None:
        n_bins_x = NUM_BINS_DEFAULT
    if n_bins_y is None:
        n_bins_y = n_bins_x
    
    values_a, values_b = gen_input(32, l) 

    bin_edges_x = np.linspace(min(values_a), max(values_a), n_bins_x + 1)
    bin_edges_y = np.linspace(min(values_b), max(values_b), n_bins_y + 1)

    ids_a, ids_b = get_ids(l, intersection_size)
    print_hist2d(ids_a, ids_b, values_a, values_b, bin_edges_x, bin_edges_y)

    return (ids_a, values_a), (ids_b, values_b), (bin_edges_x, bin_edges_y)


def print_hist2d(ids_a, ids_b, values_a, values_b, bin_edges_x, bin_edges_y):
    input_size = len(values_a)
    num_bins_x = len(bin_edges_x) - 1
    num_bins_y = len(bin_edges_y) - 1

    histogram = [[0] * num_bins_y for _ in range(num_bins_x)]
    
    for i in range(input_size):
        if ids_a[i] != ids_b[i]:
            continue
        x_val = values_a[i]
        y_val = values_b[i]
        
        x_index = 0
        y_index = 0

        # Formula for binning is bin[i-1] < x <= bin[i]
        for x_i in range(1, len(bin_edges_x)):
            if x_val <= bin_edges_x[x_i]:
                x_index = x_i - 1 # bin index
                break
        
        for y_i in range(1, len(bin_edges_y)):
            if y_val <= bin_edges_y[y_i]:
                y_index = y_i - 1 # bin index
                break

        histogram[x_index][y_index] += 1

    print("2D Histogram (Text Representation):")

    try:
        # Print the y-axis labels (bin edges)
        print("    ", end="")
        for x_bin in bin_edges_x:
            print(f"{round(x_bin, 2):>5}", end=" ")
        print()
        
        # Print the histogram rows
        for i, row in enumerate(histogram):
            print(f"{round(bin_edges_y[i], 2):>5} ", end="")  # Print x-axis labels (bin edges)
            for count in row:
                print(f"{count:>5}", end=" ")  # Print the counts for each bin
            print()
        print(f"{round(bin_edges_y[-1], 2):>5} ", end="")  # Print x-axis labels (bin edges)
    except IndexError: # If the dimensions are different or something else goes wrong, just print the raw data
        print("Error printing histogram, printing raw data instead:")
        for y in range(num_bins_y):
            for x in range(num_bins_x):
                print(f"Bin ({x}, {y}): {histogram[x][y]}")


if __name__ == "__main__":
    PROGRAMS = {
        "xtabs": gen_xtabs_input,
        "linreg": gen_linreg_input,
        "hist2d": gen_hist2d_input
    }
    parser = argparse.ArgumentParser(
        description='generates input for mp-spdz sample programs')
    
    parser.add_argument('-e', default="xtabs", choices = PROGRAMS,
        help="program selection")
    parser.add_argument('-l', default=10, type=int, 
        help="array length")
    parser.add_argument('-i', default=0.5, type=float,
        help="intersection size, i.e. the probability that a user in alice's input is also in bob's input (default: 0.5)")
    parser.add_argument('-x', type=int,
        help="number of categories, features or bins of alice (depending on the program)")
    parser.add_argument('-y', type=int,
        help="number of categories, labels or bins of bob (depending on the program)")
    
    args = parser.parse_args()

    create_dirs(args.e)

    program_function = PROGRAMS.get(args.e)

    if program_function:
        data = program_function(args.l, args.i, args.x, args.y)
        alice_data = data[0]
        bob_data = data[1]
        write_to_csv(args.e, PARTY_ALICE, *alice_data)
        write_to_csv(args.e, PARTY_BOB, *bob_data)
        if len(data) > 2:   # If the program has public data, write it to the public directory
            write_to_csv(args.e, PARTY_PUBLIC, *data[2]) # Pandas cannot register a csv with differing ammounts of items between columns which is why x and y must be the same for hist2d in this version

    else:
        print(f"Unknown program: {args.e}") # Should not happen