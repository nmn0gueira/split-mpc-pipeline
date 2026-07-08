from Compiler.instructions import closeclientconnection
from Compiler.library import accept_client_connection, do_while, for_range, if_, listen_for_clients, print_ln, start_timer, stop_timer
from Compiler.types import Array, MemValue, regint, sint, sfix

PORTNUM = 14000
MAX_NUM_CLIENTS = 8


class ClientManager:
    """Owns the socket lifecycle for as-server mode.

    Accepts connections from client-input.x processes, exposes their
    socket IDs for input reading, and reveals computation output back
    to them before closing connections.
    """

    def __init__(self):
        listen_for_clients(PORTNUM)
        print_ln('Listening for client connections on base port %s', PORTNUM)

        self.sockets = Array(MAX_NUM_CLIENTS, regint)
        self.number_clients = MemValue(regint(0))
        self._client_ids = Array(MAX_NUM_CLIENTS, sint)
        self._seen = Array(MAX_NUM_CLIENTS, regint)
        self._seen.assign_all(0)

        stop_timer()

        @do_while
        def _accept_all():
            client_socket_id = accept_client_connection(PORTNUM)
            last = regint.read_from_socket(client_socket_id)
            self.sockets[client_socket_id] = client_socket_id
            self._client_ids[client_socket_id] = client_socket_id
            self._seen[client_socket_id] = 1
            @if_(last == 1)
            def _():
                self.number_clients.write(client_socket_id + 1)
            return (sum(self._seen) < self.number_clients) + (self.number_clients == 0)

        start_timer()

    def reveal_output(self, labeled_outputs):
        def size_of(val):
            if hasattr(val, 'shape'):
                n = 1
                for s in val.shape:
                    n *= s
                return n
            else:
                return len(val)
            
        def get_basic_type(val):
            if hasattr(val, 'shape'):
                return type(val[0])
            else:
                return type(val)
            
        def get_type_id(secret_type):
            if secret_type == sint:
                return sint(0)
            elif secret_type == sfix:
                return sint(1)
            else:
                raise AttributeError(f"Unhandled type id: {secret_type}")

        for _, val in labeled_outputs:
            length = size_of(val)
            basic_type = get_basic_type(val)
            sint.reveal_to_clients(self.sockets.get_sub(self.number_clients), [sint(length), get_type_id(basic_type)])
            if hasattr(val, 'shape'):
                val.reveal_to_clients(self.sockets.get_sub(self.number_clients))
            else:
                type(val).reveal_to_clients(self.sockets.get_sub(self.number_clients), [val])
    

    def close(self):
        sint.reveal_to_clients(self.sockets.get_sub(self.number_clients), [sint(-1), sint(-1)])
        @for_range(self.number_clients)
        def _(i):
            closeclientconnection(i)
