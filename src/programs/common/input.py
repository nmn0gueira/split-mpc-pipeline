from abc import abstractmethod

from Compiler.library import for_range_opt, print_ln
from Compiler.types import sint, sintbit, Matrix, Array

from common.client import ClientManager


class InputFactory:
    """ InputFactory.

    :param compiler: The compiler instance to use for parsing options and creating inputs.

    Input-related compiler options will be added to the compiler's argument parser in the constructor. These include:
    - --protocol: The input protocol to use. One of 'psi', 'cpsi', 'ps3i', 'ps3i-xor', 'pid'.
    - --share-type: For 'cpsi' protocol, the type of share to use. One of 'xor' or 'add32'.
    - --as-server: Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input.
    """
    def __init__(self, compiler):
        self.compiler = compiler
        self.compiler.parser.add_option("--protocol", dest="protocol", type=str, help="one of psi, cpsi, ps3i, ps3i-xor, pid")
        self.compiler.parser.add_option("--share-type", dest="share_type", type=str, help="for cpsi only: xor or add32")
        self.compiler.parser.add_option("--as-server", dest="as_server", action="store_true", help="Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input")

    def create_input(self):
        """ Factory method to create an Input instance based on the compiler options specified.

        Obviously, this will not work if the specified options at init have not been parsed yet, so the caller must ensure that compiler.parse_args() has been called before invoking this method.
        """
        protocol = self.compiler.options.protocol
        share_type = self.compiler.options.share_type
        as_server = self.compiler.options.as_server

        if protocol == 'psi':
            return PsiInput(as_server)
        elif protocol == 'pid':
            return PrivateIdInput(as_server)
        elif protocol == 'cpsi':
            return CircuitPsiInput(as_server, share_type)
        elif protocol == 'ps3i-xor':
            return CrossPsiXorInput(as_server)
        elif protocol == 'ps3i':
            return CrossPsiInput(as_server)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")


class Input:
    """ Input.

    Abstract base class for different types of input taking based on previously executed two-party computation protocols for private matching within MP-SPDZ.
    :param as_server: Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input.
    """
    def __init__(self, as_server):
        self.as_server = as_server
        self.client = ClientManager() if as_server else None

    def reveal_output(self, labeled_outputs):
        if self.as_server:
            self.client.reveal_output(labeled_outputs)
        else:
            for label, val in labeled_outputs:
                print_ln('%s: %s', label, val.reveal())

    def close(self):
        if self.as_server:
            self.client.close()

    @abstractmethod
    def get_flag(self, rows):
        """ Get the flag array indicating which rows are valid for computation (e.g. which rows correspond to intersecting items). Only needed for some protocols (e.g. Private-ID, Circuit-PSI), so can return None if not applicable. """
        pass

    @abstractmethod
    def get_array(self, rows, party, secret_type):
        """ Get an input array.

        :param rows: The number of rows in the input array.
        :param party: The party from which to get the input (e.g. 0 for Alice, 1 for Bob).
        :param secret_type: The type of the elements in the array (e.g. sint or sfix).
        """
        pass

    @abstractmethod
    def get_matrix(self, rows, alice_cols, bob_cols):
        """ Get an input matrix. Only needed for some protocols, so can return None if not applicable.

        :param rows: The number of rows in the input matrix.
        :param alice_cols: The number of columns in the input matrix that belong to Alice.
        :param bob_cols: The number of columns in the input matrix that belong to Bob.
        """
        pass


class PsiInput(Input):
    """ PsiInput. Implements input retrieval. Assumes the previously executed protocol was a private set intersection (PSI) protocol. Since we are already only dealing with intersection items, all rows can be considered for computation.

    :param as_server: Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input.
    """
    def __init__(self, as_server):
        super().__init__(as_server)

    def get_flag(self, rows):
        return None

    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        if self.as_server:
            array.assign_vector(secret_type.receive_from_client(1, self.client.sockets[party], size=rows)[0])
        else:
            array.input_from(party)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols, secret_type=sint):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, secret_type)
        if self.as_server:
            for i in range(alice_cols):
                matrix.set_column(i, secret_type.receive_from_client(1, self.client.sockets[0], size=rows)[0])
            for i in range(bob_cols):
                matrix.set_column(alice_cols + i, secret_type.receive_from_client(1, self.client.sockets[1], size=rows)[0])
        else:
            for i in range(alice_cols):
                matrix.set_column(i, secret_type.get_input_from(0, size=rows))
            for i in range(bob_cols):
                matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows))
        return matrix


class PrivateIdInput(Input):
    """ PrivateIdInput. Implements input retrieval. Assumes the previously executed protocol was the Private-ID protocol. The flag array indicates which rows are valid for computation (i.e. which rows correspond to intersecting items). More details in match/README.md.

    :param as_server: Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input.
    """
    def __init__(self, as_server):
        super().__init__(as_server)

    def get_flag(self, rows):
        flag = Array(rows, sintbit)
        flag.input_from(0)
        flag[:] &= sintbit.get_input_from(1, size=rows)
        return flag

    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        array.input_from(party)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols, secret_type=sint):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, secret_type)
        for i in range(alice_cols):
            matrix.set_column(i, secret_type.get_input_from(0, size=rows))
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, secret_type.get_input_from(1, size=rows))
        return matrix


class CircuitPsiInput(Input):
    """ CircuitPsiInput. Implements input retrieval. Assumes the previously executed protocol was a variant of the Circuit-PSI protocol. The flag array indicates which rows are valid for computation (i.e. which rows correspond to intersecting items). More details in match/README.md.

    :param as_server: Whether to run the input module as a server (listening for client connections), as opposed to locally sourcing the input.
    :param share: The type of shares to reconstruct. One of 'xor' or 'add32'.
    """
    def __init__(self, as_server, share):
        super().__init__(as_server)
        self.share = share
        if self.share not in ['xor', 'add32']:
            raise ValueError(f"Unsupported share type: {self.share}")

    def get_flag(self, rows):
        flag = Array(rows, sintbit)
        flag.input_from(0)
        flag[:] ^= sintbit.get_input_from(1, size=rows)
        return flag

    def get_array(self, rows, party, secret_type):
        if party == 0:
            array = Array(rows, secret_type)
            if self.share == 'add32':
                array[:] = (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % 2**32
            else:
                @for_range_opt(rows)
                def _(i):
                    array[i] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
        else:  # party == 'b'
            array = Array(rows, secret_type)
            array.input_from(1)
        return array

    def get_matrix(self, rows, alice_cols, bob_cols, secret_type=sint):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, secret_type)
        mod = 2**32
        for i in range(alice_cols):
            if self.share == 'add32':
                matrix.set_column(i, (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % mod)
            else:
                @for_range_opt(rows)
                def _(j):
                    matrix[j][i] = sint.bit_compose(x.bit_xor(y)
                                for x,y in zip(
                                    sint.get_input_from(0).bit_decompose(),
                                    sint.get_input_from(1).bit_decompose()))
        for i in range(bob_cols):
            matrix.set_column(alice_cols + i, sint.get_input_from(1, size=rows))
        return matrix


class CrossPsiInput(Input):
    """
    CrossPsiInput. Implements input retrieval. Assumes the previously executed protocol was the PS3I protocol (additive shares variant). The input is reconstructed by summing the shares from both parties and only includes valid rows for computation. More details in match/README.md.
    """

    def __init__(self, as_server):
        super().__init__(as_server)

    def get_flag(self, rows):
        return None

    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        array[:] = (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % 2**64
        return array

    def get_matrix(self, rows, alice_cols, bob_cols, secret_type=sint):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, secret_type)
        mod = 2**64
        for i in range(num_cols):
            matrix.set_column(i, (sint.get_input_from(0, size=rows) + sint.get_input_from(1, size=rows)) % mod)
        return matrix


class CrossPsiXorInput(Input):
    """
    CrossPsiXorInput. Implements input retrieval. Assumes the previously executed protocol was the PS3I protocol (XOR shares variant). The input is reconstructed by summing the shares from both parties and only includes valid rows for computation. More details in match/README.md.
    """
    def __init__(self, as_server):
        super().__init__(as_server)

    def get_flag(self, rows):
        return None

    def get_array(self, rows, party, secret_type):
        array = Array(rows, secret_type)
        @for_range_opt(rows)
        def _(i):
            array[i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return array

    def get_matrix(self, rows, alice_cols, bob_cols, secret_type=sint):
        num_cols = alice_cols + bob_cols
        matrix = Matrix(rows, num_cols, secret_type)
        for i in range(num_cols):
            @for_range_opt(rows)
            def _(j):
                matrix[j][i] = sint.bit_compose(x.bit_xor(y)
                            for x,y in zip(
                                sint.get_input_from(0).bit_decompose(),
                                sint.get_input_from(1).bit_decompose()))
        return matrix
