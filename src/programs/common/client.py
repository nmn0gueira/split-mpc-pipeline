from Compiler.instructions import closeclientconnection
from Compiler.library import accept_client_connection, for_range, listen_for_clients, print_ln, runtime_error_if, start_timer, stop_timer
from Compiler.types import Array, regint, sint, sfix

PORTNUM = 14000


class ClientManager:
    """Owns the socket lifecycle for as-server mode.

    Accepts connections from client-input.x processes, exposes their
    socket IDs for input reading, and reveals computation output back
    to them before closing connections.
    """

    def __init__(self, n_clients):
        listen_for_clients(PORTNUM)
        print_ln('Listening for client connections on base port %s', PORTNUM)

        self.number_clients = n_clients
        self.sockets = Array(n_clients, regint)
        self._seen = Array(n_clients, regint)

        stop_timer()

        @for_range(n_clients)
        def _(i):
            client_socket_id = accept_client_connection(PORTNUM)
            self.sockets[client_socket_id] = client_socket_id
            self._seen[client_socket_id] = 1

        runtime_error_if(sum(self._seen) != n_clients, 'connection problems')

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
                return get_basic_type(val[0])
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
