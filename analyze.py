import ast
import collections
import itertools
import os

import networkx as nx
import nxpd

from Node import Node, ReferenceNode, ConstantNode, CallNode, ArgumentNode

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.join(BASE_PATH, 'examples')


class ExpressionVisitor(ast.NodeVisitor):

    def __init__(self):
        self.nodes = collections.defaultdict(list)
        self._fn_decl_visited = False

    def mk_node(self, ast_node):
        node = Node(ast_node)
        self.nodes[ast_node].append(node)
        return node

    def assign_value(self, target, value):
        if isinstance(target, ast.Tuple):  # x,y = [1,2]
            raise NotImplemented('Tuple assigment')
        graph_node = self.mk_node(target)
        graph_node.depends_on.append(value)
        return graph_node

    def visit_Assign(self, node):
        graph_node = self.mk_node(node)
        value = self.visit(node.value)
        graph_node.depends_on.append(value)
        for target in node.targets:
            self.assign_value(target, value)
        return graph_node

    def visit_AugAssign(self, node):
        graph_node = self.mk_node(node)
        value = self.visit(node.value)
        graph_node.depends_on.append(value)
        self.assign_value(node.target, value)
        target = self.visit(node.target)
        graph_node.depends_on.append(target)
        return graph_node

    def visit_BinOp(self, node):
        graph_node = self.mk_node(node)
        lhs = self.visit(node.left)
        rhs = self.visit(node.right)
        graph_node.depends_on += [lhs, rhs]
        return graph_node

    def visit_BoolOp(self, node):
        graph_node = self.mk_node(node)
        values = [self.visit(it) for it in node.values]
        graph_node.depends_on += values
        return graph_node

    def visit_Compare(self, node):
        graph_node = self.mk_node(node)
        values = [self.visit(it) for it in node.ops]
        graph_node.depends_on += values
        return graph_node

    def visit_arguments(self, node):
        for arg in node.args:
            self.visit(arg)
        return None

    def visit_arg(self, node):
        graph_node = ArgumentNode(node)
        self.nodes[node].append(graph_node)
        return graph_node

    def visit_Call(self, node):
        func = ReferenceNode(node.func)
        graph_node = CallNode(node, func)
        self.nodes[node.func].append(func)
        self.nodes[node].append(graph_node)

        arguments = [self.visit(arg) for arg in itertools.chain(node.args, node.keywords)]
        graph_node.depends_on += arguments

        return graph_node

    def visit_Return(self, node):
        graph_node = self.mk_node(node)
        value = self.visit(node.value)
        graph_node.depends_on.append(value)
        return graph_node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            ref_node = ReferenceNode(node)
            self.nodes[node].append(ref_node)
        elif isinstance(node.ctx, ast.Store):
            ref_node = self.mk_node(node)
        else:
            raise Exception('Unexpected name ctx: ', node.id, node.ctx)
        return ref_node

    def visit_Constant(self, node):
        const_node = ConstantNode(node, node.value)
        self.nodes[node].append(const_node)
        return const_node

    def visit_Num(self, node):
        const_node = ConstantNode(node, node.n)
        self.nodes[node].append(const_node)
        return const_node

    def visit_While(self, node):
        graph_node = self.mk_node(node)
        test = self.visit(node.test)
        graph_node.depends_on.append(test)
        self.generic_visit(node)
        return graph_node

    def visit_If(self, node):
        graph_node = self.mk_node(node)
        test = self.visit(node.test)
        graph_node.depends_on.append(test)
        self.generic_visit(node)
        return graph_node

    def visit_For(self, node):
        graph_node = self.mk_node(node)
        iterable = self.visit(node.iter)
        graph_node.depends_on.append(iterable)
        self.generic_visit(node)
        return graph_node

    def visit_FunctionDef(self, node):
        if self._fn_decl_visited:  # don't go to nested functions
            return
        self._fn_decl_visited = True
        self.generic_visit(node)

    def generic_visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, None)
        if visitor is None:
            print('Not implemented for node: ', node)
        super(ExpressionVisitor, self).generic_visit(node)


class ReferenceResolver(ast.NodeVisitor):
    def __init__(self, target_node):
        self.target_node = target_node
        self.resolved_node = None
        self.continue_resolution = True
        self.names = {}

    def visit_arg(self, node):
        self.names[node.arg] = node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.names[node.id] = node
        elif isinstance(node.ctx, ast.Load) and self.target_node == node:
            if node.id not in self.names:
                print('Name is not resolved: ', node.id)
            self.resolved_node = self.names.get(node.id, None)
            self.continue_resolution = False

    def visit(self, node):
        if not self.continue_resolution:
            return
        super(ReferenceResolver, self).visit(node)


def visualize_graph(nodes):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
        if isinstance(node, ReferenceNode) and node.referenced_node is not None:
            G.add_edge(node, node.referenced_node)
        if node.depends_on is None:
            continue
        for dependency in node.depends_on:
            G.add_edge(node, dependency)
    # nxpd.nxpdParams['show'] = 'ipynb'
    nxpd.draw(G, show=True)


class FunctionLevelAnalyzer(ast.NodeVisitor):

    def merge_nodes(self, nodes):
        merged_nodes = {}
        for ast_node, graph_nodes in nodes.items():
            if not graph_nodes:
                merged_nodes[ast_node] = []
            elif len(graph_nodes) == 1:
                merged_nodes[ast_node] = graph_nodes[0]
            else:
                first = graph_nodes[0]
                if all(it.ast_node == first.ast_node and type(it) == type(first) for it in graph_nodes):
                    if first.depends_on is not None:
                        for elem in graph_nodes[1:]:
                            first.depends_on += elem.depends_on
                    merged_nodes[ast_node] = first
                else:
                    raise NotImplementedError('Merge is not implemented')

        result = {
            ast_node: self.simplify_dependencies(graph_node)
            for ast_node, graph_node in merged_nodes.items()
        }

        return result

    def simplify_dependencies(self, node):
        if node.depends_on is None:
            return node
        current_deps = node.depends_on
        node.depends_on = list(set(current_deps))
        return node

    def visit_FunctionDef(self, node):
        analyzer = ExpressionVisitor()
        analyzer.visit(node)
        nodes = self.merge_nodes(analyzer.nodes)
        references = [it for it in nodes.values() if isinstance(it, ReferenceNode)]
        for ref in references:
            self.resolve_reference(ref, node, nodes)
        result_nodes = list(nodes.values())
        visualize_graph(result_nodes)

    def resolve_reference(self, reference, scope, nodes):
        if not isinstance(reference.ast_node, ast.Name):
            raise NotImplementedError("Non name reference: ", reference)
        resolver = ReferenceResolver(reference.ast_node)
        resolver.visit(scope)
        if resolver.resolved_node is None:
            print('Node is not resolved: ', reference.ast_node.id)
        resolved_graph_node = resolver.resolved_node and nodes[resolver.resolved_node]
        reference.referenced_node = resolved_graph_node


def main():
    files = [os.path.join(EXAMPLE_DIR, f) for f in os.listdir(EXAMPLE_DIR)]
    sources = [open(f).read() for f in files]
    asts = [ast.parse(f) for f in sources]
    analyzer = FunctionLevelAnalyzer()
    for _ast in asts:
        analyzer.visit(_ast)


if __name__ == '__main__':
    main()
