# Matching Protocols

## Submodules
These provide the implementations for the protocols used for matching datasets.
- `Kunlun` - An OpenSSL wrapper containing implementations of private set operation protocols. Most notably for this project, the state-of-the-art Private-ID protocol is used.
- `Private-ID` - A collection of algorithms to match records between two or more parties. This project makes use of their PS3I and PS3I-XOR protocol implementations.
- `volepsi` - A repository including the state-of-the-art PSI and Circuit-PSI protocol implementations.

Each submodule includes implementation details and references to the relevant academic papers.


## Protocol Notes
For additional runtime arguments or other implementation details, check the respective submodule's repository.

### Private Set Intersection (PSI)
#### Output format
One row per item in the intersection, containing the sender's feature columns. Order follows the PSI binary's output.
```
feature1, feature2, ...
feature1, feature2, ...
...
```

#### Example command
```bash
# Bob (server/receiver)
python3 scripts/match.py --input path/to/bob.csv --output path/to/bob_out.csv --address 0.0.0.0:10010 psi
# Alice (client/sender)
python3 scripts/match.py --input path/to/alice.csv --output path/to/alice_out.csv --address 127.0.0.1:10010 psi
```

### Circuit-PSI
#### Output format
The output of Circuit-PSI differs between the party that is executing the protocol. Both parties include a first column with a flag bits and a column of shares for each of the sender's features. The client/sender will additionally have its own associated data appended.

- Sender
```
flag, share1, ...
flag, share2, ...
...
```
- Receiver
```
flag, share1, ..., own_feature1, ...
flag, share2, ..., own_feature1, ...
...
```
The XOR of flag values in the same row indicates if a row is in the intersection.

#### Example command
```bash
# Alice (client/sender, party 0)
python3 scripts/match.py --input path/to/alice.csv --output path/to/alice_out.csv --address 127.0.0.1:10010 cpsi -add32
# Bob (server/receiver, party 1)
python3 scripts/match.py --input path/to/bob.csv --output path/to/bob_out.csv --address 0.0.0.0:10010 cpsi -add32 -senderColumns 1
```
The `-add32` flag selects additive mod 2^32 secret sharing. Omit it for XOR secret sharing. The current MP-SPDZ programs expect Alice to always be party 0.

### Private-ID
#### Output format
One row per item in the union of both parties' sets. The first column is a flag (1 if the given party has this row in their set, 0 otherwise), followed by this party's feature values at matched positions and 0 elsewhere.
```
flag, feature1, ...
flag, feature1, ...
...
```
A row is in the intersection if the AND of their flag bits is 1.

#### Example command
```bash
# Bob (server)
python3 scripts/match.py --input path/to/bob.csv --output path/to/bob_out.csv --address 0.0.0.0:10010 pid --log_sender 14 --log_receiver 14
# Alice (client)
python3 scripts/match.py --input path/to/alice.csv --output path/to/alice_out.csv --address 127.0.0.1:10010 pid --log_sender 14 --log_receiver 14
```
The `--log_sender` and `--log_receiver` arguments are the log$_2$ of each party's set size. If a set is not an exact power of 2, specify the closest next power of 2 to pad the set with random identifiers automatically.

### PS3I(-XOR)
#### Output format
- PS3I
```
cshare1, sshare1
cshare2, sshare2
...
```
The client's share column comes first, then the server's. PS3I supports only one feature per party. Secret sharing is additive mod 2^64.

- PS3I-XOR
```
sshare1, ..., cshare1, ...
sshare2, ..., cshare2, ...
...
```
All server share columns come first, followed by all client share columns.

#### Example command
```bash
# Alice (server, party 0)
python3 scripts/match.py --input path/to/alice.csv --output path/to/alice_out.csv --address 0.0.0.0:10010 <ps3i|ps3i-xor> --no-tls
# Bob (client, party 1)
python3 scripts/match.py --input path/to/bob.csv --output path/to/bob_out.csv --address http://127.0.0.1:10010 <ps3i|ps3i-xor> --no-tls
```


## Misc
Protocols that output secret shares (`cpsi`, `ps3i`, `ps3i-xor`) do not natively support float or negative values, as shares are unsigned integers. This a limitation of the current implementations.
