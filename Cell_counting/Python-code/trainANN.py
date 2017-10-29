from keras.models import Sequential
from keras.layers import Dense, Activation
import h5py

import numpy as np


print "Beginning ANN architecture"

model = Sequential()
model.add(Dense(120, input_dim=10000))
model.add(Activation('sigmoid'))
model.add(Dense(20))
model.add(Activation('sigmoid'))
model.add(Dense(1))
model.compile(optimizer = 'sgd',loss = 'mean_squared_error')

X = np.load('X.npy')
y = np.load('y.npy')

model.fit(X,y)

print "ANN trained. Saving model to file"

model.save("trainedANN.h5")