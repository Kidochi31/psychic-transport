from connection import Connection


class ConnectionState:
    def __init__(self,
                 connections: list[Connection],
                 new_connections: list[Connection],
                 disconnections: list[Connection]):
        self.connections = connections
        self.new_connections = new_connections
        self.disconnections = disconnections