
class Node:
    def __init__(self, name, ast_node):
        self.ast_node = ast_node
        self.name = name
        self.in_edges = []
        self.out_edges = []


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.names = {}

    def resolve_name(self, name):
        scope = self
        while scope is not None and name not in scope.names:
            scope = scope.parent
        if scope is None or name not in scope.names:
            raise Exception(f'Name {name} is not resolved')
        return scope.names[name]

    def create_scope(self):
        return Scope(parent=self)

    def add_name(self, name, node):
        self.names[name] = Node(name, node)
