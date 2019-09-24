import ast
import os

from Scope import Scope

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.join(BASE_PATH, 'examples')


class ScopedVisitor(ast.NodeVisitor):
    def __init__(self, scope):
        self.scope = scope

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.scope.add_name(node.id, node)


class FunctionLevelAnalyzer(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        scope = Scope()
        ScopedVisitor(scope).visit(node)
        print(scope)


def main():
    files = [os.path.join(EXAMPLE_DIR, f) for f in os.listdir(EXAMPLE_DIR)]
    sources = [open(f).read() for f in files]
    asts = [ast.parse(f) for f in sources]
    analyzer = FunctionLevelAnalyzer()
    for _ast in asts:
        analyzer.visit(_ast)


if __name__ == '__main__':
    main()
