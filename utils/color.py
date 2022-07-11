import math


def is_same_color(rgb1, rgb2, tolerance=3):
    return abs(rgb1[0] - rgb2[0]) <= tolerance and abs(rgb1[1] - rgb2[1]) <= tolerance and abs(rgb1[2] - rgb2[2]) <= tolerance
