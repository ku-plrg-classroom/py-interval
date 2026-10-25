def window(xs, n):
    i = 0
    j = 0
    s = 0
    while i < n:
        s = s + xs[i]
        i = i + 1
        if j + 3 < i or 10 < s:
            s = s + -xs[j]
            j = j + 1
    return s
