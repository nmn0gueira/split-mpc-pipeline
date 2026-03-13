# Class for simpler functions with no need for a class structure
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