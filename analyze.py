import ast
import os

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.join(BASE_PATH, 'examples')


class FunctionLevelAnalyzer(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        print(node)


def main():
    files = [os.path.join(EXAMPLE_DIR, f) for f in os.listdir(EXAMPLE_DIR)]
    sources = [open(f).read() for f in files]
    asts = [ast.parse(f) for f in sources]
    analyzer = FunctionLevelAnalyzer()
    for _ast in asts:
        analyzer.visit(_ast)


if __name__ == '__main__':
    main()
