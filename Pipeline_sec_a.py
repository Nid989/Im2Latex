import os
import numpy as np
import tensorflow as tf
from tensorflow import keras

class form_or_nonform:

    def __init__(self, model_path):

        self.loc_model = model_path
        # initialize file_name = None
        self.file_name = None
        
        # image dimension...
        self.height = 180
        self.width = 180

        # pred_class setting it to None initially...
        self.pred_class = None

        # load model...
        self.load_model()

    def load_model(self):
        self.model = keras.models.load_model(self.loc_model)

    def model_summary(self):
        self.model.summary()

    def predict_class(self, file_path):
        self.file_name = file_path # E.g. temp.png
        img = tf.io.read_file(self.file_name)
        img = tf.image.decode_png(img, channels=3)
        img.set_shape([None, None, 3])
        img = tf.image.resize(img, (self.height, self.width))
        img = np.expand_dims(img, 0)
        pred = self.model.predict(img)
        self.pred_class = np.argmax(pred) 

if __name__ == '__main__':
    f_or_nf = form_or_nonform('form_vs_non_form')
    f_or_nf.predict_class('temp.png')
    print(f_or_nf.pred_class)
