def bar(a):
    return a + 1


def foo(x, y):
    a = x - bar(y)
    for i in range(a):
        x += 1
    return x * y
