# Generate a bunch of ellipses in an image

import cv2
import numpy as np
import random
import math
import matplotlib.pyplot as plt

def generateEllipse(canvas_size = (100,100,3),
                    min_size = 5,
                    max_size = 14,
                    number_range = 11,
                    min_e = 0,
                    max_e = 0.7,
                    max_back_alpha = 0.4,
                    min_ellipse_alpha = 0.6):
    img = np.ones(canvas_size, np.uint8)
    back_alpha = random.random() * max_back_alpha
    img = int(math.ceil(back_alpha * 255)) * img

    ellipse_alpha = min_ellipse_alpha + (1 - min_ellipse_alpha) * random.random()

    n = random.randrange(number_range)
    positions = np.zeros((n,2))
    e = min_e + (max_e - min_e) * random.random()
    height, width, colors = canvas_size

    for i in range(n):
        position = (int(math.floor(random.randrange(width))),
                    int(math.floor(random.randrange(height))))
        positions[i] = position
        major_axis = random.randrange(min_size, max_size)
        minor_axis = int(math.floor(major_axis / math.sqrt(1 - math.pow(e, 2))))
        axes = major_axis, minor_axis
        color = math.ceil(ellipse_alpha * 255)
        color = color, color, color
        img = cv2.ellipse(img, position, axes,
                          random.randrange(0, 360),
                          0, 360, color, -1)



    return img,n

