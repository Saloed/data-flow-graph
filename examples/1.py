def foo(x, y):
    a = x - bar(y)
    for i in range(a):
        x += 1
    y = 5
    return x * y
