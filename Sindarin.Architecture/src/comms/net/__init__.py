
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR


class Router(object):
    
    class TCP(object):
        def socket(self, port):
            s = socket(AF_INET, SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind(('', port))
            s.listen(5)
            return s
        def done(self, client_socket):
            client_socket.close()
    
    class ThreadPerConnection(object):
        def start(self, runnable, on_finish=lambda:0):
            import thread
            def body():
                try:
                    runnable()
                finally:
                    on_finish()
            thread.start_new(body, ())
    
    def __init__(self, port=6065):
        self.port = port
        self.handler = lambda stream, context: None
        self.net_protocol = self.TCP()
        self.branching_policy = self.ThreadPerConnection()
        
    def __call__(self):
        accept_socket = self.net_protocol.socket(self.port)
        while True:
            client_socket, client_address = accept_socket.accept()
            context = [client_address]
            def handle():
                self.handler(client_socket, context)
            def finalize():
                self.net_protocol.done(client_socket)
            self.branching_policy.start(handle, on_finish=finalize)



if __name__ == "__main__":
    from telnet import Telnet
    r = Router()
    def handler(stream, context):
        print context
        while True:
            x = stream.recv(1024)
            if x: print `x`
            if not x or x.endswith(Telnet.EOF) or x.endswith(Telnet.BRK): break
        stream.send("Arrigato! Sayonara!\n")
    r.handler = handler
    r()
    