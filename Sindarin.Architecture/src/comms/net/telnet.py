


class Telnet(object):
    EOF = '\xff\xec'
    BRK = '\xff\xf3'


class ShellPipeHandler(object):
    """
    Serves a connection by directing the incoming data to a pipe, and sending
    back data from the other end of the pipe.
    This allows a user-level independent program to operate as a service.
    
    E.g. when used with command="sort", a client may have the following 
    session:
        % telnet server 6065
        Connected to server.
        Escape character is '^]'.
        joe
        hisa
        ishi
        ^]
        telnet> send eof
        hisa
        ishi
        joe
        Connection closed by foreign host.
    """
    
    def __init__(self, command):
        self.command = command
        
    def __call__(self, stream, context):
        import subprocess
        p = subprocess.Popen(self.command,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             shell=True)
        try:
            self.from_socket_to_pipe(stream, p.stdin)
        finally:
            p.stdin.close()
            self.from_pipe_to_socket(p.stdout, stream)
            p.wait()
        
    def from_socket_to_pipe(self, stream, pipe):
        buf = ''
        while True:
            inp = buf + stream.recv(1024)
            buf = ''
            if inp == '':
                break
            if inp.endswith(Telnet.EOF) or inp.endswith(Telnet.BRK):
                pipe.write(inp[:-2])
                break
            if inp.endswith(Telnet.EOF[0]):
                inp, buf = inp[:-1], inp[-1]
            pipe.write(inp)
    
    def from_pipe_to_socket(self, pipe, stream):
        while True:
            out = pipe.read(1024)
            if out == '': break
            stream.send(out)



class TelnetClient(object):
    """
    Connection to a remote Telnet service through TCP.
    """
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        
    def read(self):
        buf = []
        while True:
            x = self.socket().recv(1024)
            if not x: break
            buf.append(x)
        return ''.join(buf)
        
    def write(self, data):
        self.socket().send(data)
            
    def close(self):
        self.socket().send(Telnet.EOF)
        
    def socket(self):
        from socket import socket, AF_INET, SOCK_STREAM
        if self.client_socket is None:
            self.client_socket = socket(AF_INET, SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
        return self.client_socket
    
    def __call__(self, entire_input):
        self.write(entire_input)
        self.close()
        entire_output = self.read()
        return entire_output



if __name__ == '__main__':
    from comms.net import Router
    r = Router()
    r.handler = ShellPipeHandler("sort")
    r()
    