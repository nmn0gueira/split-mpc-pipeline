import argparse, random, os, math, errno, string
import numpy as np
import pandas as pd
from operator import itemgetter
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

np.set_printoptions(legacy='1.25')

BASE_DIR = "data"
PARTY_ALICE = "alice"
PARTY_BOB = "bob"
PARTY_PUBLIC = "public"
BITSIZE = 32

def create_dirs(program):
    dirname = os.path.join(BASE_DIR, program)
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST: raise


def gen_input(n_bits, l):
    if (n_bits > 32):
        raise ValueError("invalid bit length---this test can only handle up to 32 bits")

    bits = int((n_bits - int(math.log(l, 2))) / 2)
    
    return [random.getrandbits(bits) for _ in range(l)]


def generate_random_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_unique_ids(count, exclude_ids=None):
    ids = set()
    exclude_ids = exclude_ids or set()
    while len(ids) < count:
        new_id = generate_random_id()
        if new_id not in ids and new_id not in exclude_ids:
            ids.add(new_id)
    return ids


def get_ids(size_a, size_b, size_intersection):
    assert size_intersection <= min(size_a, size_b), "Intersection size cannot be larger than the size of either input"
    intersection_ids = generate_unique_ids(size_intersection)
    ids_a = intersection_ids | generate_unique_ids(size_a - size_intersection, exclude_ids=intersection_ids)
    ids_b = intersection_ids | generate_unique_ids(size_b - size_intersection, exclude_ids=intersection_ids)

    return ids_a, ids_b


def gen_xtabs_input(size_a, size_b, n_categories_a, n_categories_b):
    '''
    Generates input for xtabs program. This input functions as if both parties already have their input ordered. One party has the (typically 
    categorical) value to group by (e.g. education level) and the other has the (typically continuous) values to aggregate upon (e.g. salary). The 
    output will depend on the function that is used to aggregate the values.
    '''
    categories_a, categories_b = [random.randrange(1, n_categories_a + 1) for _ in range(size_a)], [random.randrange(1, n_categories_b + 1) for _ in range(size_b)]
    values_a, values_b = gen_input(BITSIZE, size_a), gen_input(BITSIZE, size_b)

    return (categories_a, values_a), (categories_b, values_b)


def print_xtabs(categories_a, categories_b, values):
    input_len = len(categories_a)

    sums = {}
    averages = {}
    counts = {}

    frequencies = {}    # absolute frequencies
    modes = {}

    std_values = {}
    std0 = {}   # ddof=0
    std1 = {}   # ddof=1

    for i in range(input_len):
        sums[categories_a[i]] = sums.get(categories_a[i], 0) + values[i]
        counts[categories_a[i]] = counts.get(categories_a[i], 0) + 1
        std_values[categories_a[i]] = std_values.get(categories_a[i], [])
        std_values[categories_a[i]].append(values[i])

        frequency_dict = frequencies.get(categories_a[i], {})
        frequency_dict[categories_b[i]] = frequency_dict.get(categories_b[i], 0) + 1
        frequencies[categories_a[i]] = frequency_dict

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


def gen_linreg_input(size_a, size_b, n_features_a, n_features_b, return_ints=False, scale_features=True, normalize_labels=True):
    def scale_data(data):
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        return (data - mean) / std
    def normalize_data(data):
        max_value = np.max(data, axis=0)
        return data / max_value
    
    X_a, y_a = make_regression(n_samples=size_a, n_features=n_features_a, random_state=42)
    X_b, y_b = make_regression(n_samples=size_b, n_features=n_features_b, random_state=42)
    y_a = y_a.reshape(-1, 1)  # Ensure y is a 2D array with shape (size, n_labels)
    y_b = y_b.reshape(-1, 1) 

    if scale_features:
        X_a = scale_data(X_a)
        X_b = scale_data(X_b)

    if normalize_labels:
        y_a = normalize_data(y_a)
        y_b = normalize_data(y_b)

    if return_ints:
        return (np.abs(X_a).astype(np.uint64), np.abs(y_a).astype(np.uint64)), (np.abs(X_b).astype(np.uint64), np.abs(y_b).astype(np.uint64))

    return (X_a, y_a), (X_b, y_b)


def print_linreg(X, Y, split=True):
    model = LinearRegression()
    if split:
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
        model.fit(X_train, Y_train)
        print("Expected test error of model (MSE):", mean_squared_error(Y_test, model.predict(X_test)))
    else:
        model.fit(X, Y)
    print("Expected weights (w):\n", model.coef_)
    print("Expected intercept:\n", model.intercept_)


def gen_hist2d_input(size_a, size_b, n_bins_x, n_bins_y, round_edges=False):
    values_a, values_b = gen_input(BITSIZE, size_a), gen_input(BITSIZE, size_b)

    bin_edges_x = np.linspace(min(values_a), max(values_a), n_bins_x + 1)
    bin_edges_y = np.linspace(min(values_b), max(values_b), n_bins_y + 1)
    if round_edges:
        bin_edges_x = np.round(bin_edges_x).astype(int)
        bin_edges_y = np.round(bin_edges_y).astype(int)
    return values_a, values_b, (bin_edges_x, bin_edges_y)


def print_hist2d(values_a, values_b, bin_edges_x, bin_edges_y):
    input_size = len(values_a)
    num_bins_x = len(bin_edges_x) - 1
    num_bins_y = len(bin_edges_y) - 1

    histogram = [[0] * num_bins_y for _ in range(num_bins_x)]
    
    for i in range(input_size):
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
        print("    ", end="")
        for x_bin in bin_edges_x:
            print(f"{round(x_bin, 2):>5}", end=" ")
        print()
        
        for i, row in enumerate(histogram):
            print(f"{round(bin_edges_y[i], 2):>5} ", end="")
            for count in row:
                print(f"{count:>5}", end=" ")
            print()
        print(f"{round(bin_edges_y[-1], 2):>5} ", end="")
    except IndexError: # If the dimensions are different or something else goes wrong, just print the raw data
        print("Error printing histogram, printing raw data instead:")
        for y in range(num_bins_y):
            for x in range(num_bins_x):
                print(f"Bin ({x}, {y}): {histogram[x][y]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='generates input for mp-spdz sample programs')
    
    parser.add_argument('-e', default="xtabs", choices = ["xtabs", "linreg", "hist2d"],
        help="Program selection")
    parser.add_argument('-a', default=10, type=int, 
        help="Alice's input size (default: 10)")
    parser.add_argument('-b', type=int,
        help="Bob's input size (default: Alice' input size)")
    parser.add_argument('-i', type=int,
        help="Intersection size (default: half of the smallest set size)")

    xtabs_group = parser.add_argument_group('XTABS Program Arguments')
    xtabs_group.add_argument('-ca', default=4, type=int, help="Number of categories for Alice (default: 4)")
    xtabs_group.add_argument('-cb', default=4, type=int, help="Number of categories for Bob (default: 4)")

    linreg_group = parser.add_argument_group('LINREG Program Arguments')
    linreg_group.add_argument('-xa', default=5, type=int, help="Number of features for Alice (default: 5)")
    linreg_group.add_argument('-xb', default=5, type=int, help="Number of features for Bob (default: 5)")
    linreg_group.add_argument('--return-ints', action='store_true', help="Return data as integers instead of floats")

    hist2d_group = parser.add_argument_group('HIST2D Program Arguments')
    hist2d_group.add_argument('-ba', default=5, type=int, help="Number of bins for Alice (default: 5)")
    hist2d_group.add_argument('-bb', default=5, type=int, help="Number of bins for Bob (default: 5)")
    hist2d_group.add_argument('--round-edges', action='store_true', help="Round bin edges to integers")
    
    args = parser.parse_args()

    create_dirs(args.e)

    size_alice = args.a
    size_bob = args.b if args.b else args.a
    size_intersection = args.i if args.i else min(size_alice, size_bob) // 2

    ids_a, ids_b = get_ids(size_alice, size_bob, size_intersection)
    alice_data = pd.DataFrame(ids_a)
    bob_data = pd.DataFrame(ids_b)
    public_data = pd.DataFrame()

    if args.e == "xtabs":
        a, b = gen_xtabs_input(size_alice, size_bob, args.ca, args.cb)
        alice_data = pd.concat([alice_data, pd.DataFrame(zip(*a))], axis=1, ignore_index=True)
        bob_data = pd.concat([bob_data, pd.DataFrame(zip(*b))], axis=1, ignore_index=True)
        intersection_df = alice_data.merge(bob_data, on=0, how='inner')
        print_xtabs(intersection_df.iloc[:,1].values, intersection_df.iloc[:,3].values, intersection_df.iloc[:, 4].values)
    
    elif args.e == "linreg":
        a, b = gen_linreg_input(size_alice, size_bob, args.xa, args.xb, return_ints=args.return_ints)
        alice_data = pd.concat([alice_data, pd.DataFrame(np.hstack(a))], axis=1, ignore_index=True)
        bob_data = pd.concat([bob_data, pd.DataFrame(np.hstack(b))], axis=1, ignore_index=True)
        intersection_df = alice_data.merge(bob_data, on=0, how='inner')
        features_a = intersection_df.iloc[:, 1: args.xa + 1].values
        features_b = intersection_df.iloc[:, args.xa + 2: args.xa + args.xb + 2].values
        X = np.hstack((features_a, features_b))
        y = intersection_df.iloc[:, -1].values   # Use bob's labels (this will result in alice's features being less correlated with the labels though)
        print("Training linear regression model with split data into train and test sets.")
        print_linreg(X, y)
        print("Training linear regression model without splitting data into train and test sets.")
        print_linreg(X, y, split=False)

    elif args.e == "hist2d":
        a, b, public_data = gen_hist2d_input(size_alice, size_bob, args.ba, args.bb, round_edges=args.round_edges)
        alice_data = pd.concat([alice_data, pd.DataFrame(a)], axis=1, ignore_index=True)
        bob_data = pd.concat([bob_data, pd.DataFrame(b)], axis=1, ignore_index=True)
        intersection_df = alice_data.merge(bob_data, on=0, how='inner')
        public_data = pd.DataFrame(zip(*public_data))
        print_hist2d(intersection_df.iloc[:,1].values, intersection_df.iloc[:,2].values, public_data.iloc[:,0].values, public_data.iloc[:,1].values)
    
    else:
        print(f"Unknown program: {args.e}")
    
    alice_data.to_csv(os.path.join(BASE_DIR, args.e, f"{PARTY_ALICE}.csv"), index=False, header=False)
    bob_data.to_csv(os.path.join(BASE_DIR, args.e, f"{PARTY_BOB}.csv"), index=False, header=False)
    public_data.to_csv(os.path.join(BASE_DIR, args.e, f"{PARTY_PUBLIC}.csv"), index=False, header=False)