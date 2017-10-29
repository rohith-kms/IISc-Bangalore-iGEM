# dataset creation for ML cellCount algo testing

from generateEllipses import generateEllipse
import numpy as np

# parameters
IMAGE_SIZE = np.uint(100)
CANVAS_SIZE = IMAGE_SIZE, IMAGE_SIZE, 3
MIN_SIZE = np.uint(2)
MAX_SIZE = np.uint(20)
NUMBER_RANGE = np.uint(20)
MIN_E = 0
MAX_E = 0.9
MAX_BACK_ALPHA = 0.45
MIN_ELLIPSE_ALPHA = 0.65


def generateData(number):

    X = np.zeros((1,IMAGE_SIZE*IMAGE_SIZE))
    y = np.zeros(1)
    for i in range(0,number):
        I, n = generateEllipse(CANVAS_SIZE, MIN_SIZE, MAX_SIZE,
                               NUMBER_RANGE, MIN_E, MAX_E,
                               MAX_BACK_ALPHA, MIN_ELLIPSE_ALPHA)

        I = I[:,:,0]
        I = I/255.0
        I = I.reshape(1,IMAGE_SIZE*IMAGE_SIZE)
        X = np.append(X,I,0)
        y = np.append(y,n)

    np.save('X',X)
    np.save('y',y)

def unrollImage(I):
    I = I*255
    I = np.reshape(I,(IMAGE_SIZE,IMAGE_SIZE))
    img = np.zeros((IMAGE_SIZE,IMAGE_SIZE,3))
    for i in range(0,3):
        img[:,:,i] = I

    img = np.uint8(img)
    return img

generateData(10000)






