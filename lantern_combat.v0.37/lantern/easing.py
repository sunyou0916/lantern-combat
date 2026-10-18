def smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


def envelope(t, start, end, fade=0.3):
    return smooth((t-start)/fade)*smooth((end-t)/fade)
