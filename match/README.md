# Matching

## Submodules
These provide the implementations for the protocols used for matching datasets.
- `Kunlun` - An OpenSSL wrapper containing implementations of private set operation protocols. Most notably for this project, the state-of-the-art Private-ID protocol is used.
- `Private-ID` - A collection of algorithms to match records between two or more parties. This project makes use of their PS3I and PS3I-XOR protocol implementations.
- `volepsi` - A repository including the state-of-the-art PSI and Circuit-PSI protocol implementations.

Each submodule includes implementation details and references to the relevant academic papers. You can read the associated papers for further understanding of the mathematical and cryptographic underpinnings.


## Protocol Notes
This section will denote some information specific to each (matching) protocol implementation.

For other information on the protocols, such as additional runtime arguments to use or any ther specific implementation details, check the respective submodule's repository.

### Private Set Intersection
#### Example command
```
python3 scripts/match.py --input path/to/alice.csv --output path/to/output.csv --address 0.0.0.0:10010 psi
```

### Circuit-PSI
#### Output format
The output of Circuit-PSI differs between the party that is executing the protocol. Both parties include a first column with a flag bits and a column of shares for each of the sender's features.
- Sender
```
0, share1, ...
1, share2, ...
0, share3, ...
0, share4, ...
..., ..., ...
```
- Receiver
```
0, share1, ..., 0, 0, 0
1, share2, ..., 1, 2, 4
0, share3, ..., 3, 3, 1
0, share4, ..., 0, 0, 0
..., ..., ..., ..., ...,
```
The receiver additionally has its own associated data appended to each row.

#### Example command
Alice (party 0):
```
python3 scripts/match.py --input path/to/alice.csv --output path/to/output.csv --address 127.0.0.1:10010 cpsi
```
Bob (party 1):
```
python3 scripts/match.py --input path/to/bob.csv --output path/to/output.csv --address 0.0.0.0:10010 cpsi -senderColumns 1 -add32
```
The `-add32` may be removed if XOR secret sharing is preferred. The MP-SPDZ programs are written to handle input such that Alice has to be party 0 always.

### Private-ID
#### Example command
```
python3 scripts/match.py --input path/to/input.csv --output path/to/output.csv --address 0.0.0.0:10010 pid --log_sender 14 --log_receiver 14
```

The log arguments refer to the expected log 2 size of the set of the given party. To work around this restriction you can specify the closest next log 2 size value to the size of the respective set to pad the set with random identifiers.

### PS3I(-XOR)
#### Output format
- PS3I-XOR
```
sshare1, ..., ..., cshare1
sshare2, ..., ..., cshare2
sshare3, ..., ..., cshare3
sshare4, ..., ..., cshare4
..., ..., ..., ...
```
The output of PS3I-XOR is such that the CSV containing the secret shares will contain the secret shares for all of the server's features and then the secret shares for all of the client's features.

- PS3I
```
cshare1, sshare1
cshare2, sshare2
cshare3, sshare3
cshare4, sshare4
..., ...
```
The output of PS3I has the column with the shares of the client first and then the column with the shares of the server. Additionally the implementation of PS3I only allows one feature per party.

#### Example command
Alice (party 0):
```
python3 scripts/match.py --input path/to/alice.csv --output path/to/output.csv --address 0.0.0.0:10010 <ps3i-xor|ps3i> --no-tls
```
Bob (party 1):
```
python3 scripts/match.py --input path/to/bob.csv --output path/to/output.csv --address http://127.0.0.1:10010 <ps3i-xor|ps3i> --no-tls
```


### Misc

Protocols that output secret shares do not support secret sharing float values.
