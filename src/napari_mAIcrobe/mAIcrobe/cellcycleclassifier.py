import numpy as np
from skimage.util import img_as_float
from skimage.exposure import rescale_intensity
from skimage.transform import resize as skresize
from keras.utils import get_file
from keras.models import load_model

import tensorflow as tf
from tensorflow.keras import Input
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation, Flatten, RandomFlip, RandomRotation
from tensorflow.keras.layers import Conv2D, MaxPooling2D
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint, EarlyStopping

import os

class CellCycleClassifier:

    def __init__(self, fluor_fov, optional_fov, model, model_path, model_input, max_dim):

        self.prebuilts_config = {
        "S.aureus DNA+Membrane Epi": {"max_dim": 50, "model_input": "Membrane+DNA",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/cellcycle_cnn_model?raw=true'},
        "S.aureus DNA+Membrane SIM": {"max_dim": 100, "model_input": "Membrane+DNA",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/cellcycle_cnn_model?raw=true'},
        
        "S.aureus DNA Epi": {"max_dim": 50, "model_input": "DNA",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/dna_only_cellcycle_model.keras?raw=true'},
        "S.aureus DNA SIM": {"max_dim": 100, "model_input": "DNA",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/dna_only_cellcycle_model.keras?raw=true'},
        
        "S.aureus Membrane Epi": {"max_dim": 50, "model_input": "Membrane",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/membrane_only_cellcycle_model.keras?raw=true'},
        "S.aureus Membrane SIM": {"max_dim": 100, "model_input": "Membrane",'model_path':'https://github.com/HenriquesLab/napari-mAIcrobe/blob/main/docs/membrane_only_cellcycle_model.keras?raw=true'},
        }

        # depth = 11
        # self.model = Sequential()
        # self.model.add(Input(shape=(100,100,1)))

        # self.model.add(Conv2D(16, (3, 3), padding='same'))
        # self.model.add(Activation('relu'))

        # if depth > 1:
        #     self.model.add(MaxPooling2D(pool_size=(2, 2)))

        #     if depth > 2:
        #         self.model.add(Conv2D(16, (3, 3), padding='same'))
        #         self.model.add(Activation('relu'))

        #         if depth > 3:
        #             self.model.add(MaxPooling2D(pool_size=(2, 2)))

        #             if depth > 4:
        #                 self.model.add(Conv2D(16, (3, 3), padding='same'))
        #                 self.model.add(Activation('relu'))

        #                 if depth > 5:
        #                     self.model.add(MaxPooling2D(pool_size=(2, 2)))

        #                     if depth > 6:
        #                         self.model.add(Conv2D(32, (3, 3), padding='same'))
        #                         self.model.add(Activation('relu'))

        #                         if depth > 7:
        #                             self.model.add(Conv2D(32, (3, 3), padding='same'))
        #                             self.model.add(Activation('relu'))

        #                             if depth > 8:
        #                                 self.model.add(Conv2D(32, (3, 3), padding='same'))
        #                                 self.model.add(Activation('relu'))

        #                                 if depth > 9:
        #                                     self.model.add(Conv2D(32, (3, 3), padding='same'))
        #                                     self.model.add(Activation('relu'))

        #                                     if depth > 10:
        #                                         self.model.add(Flatten())
        #                                         self.model.add(Dense(100))
        #                                         self.model.add(Activation('relu'))
        # if depth <= 10:
        #     self.model.add(Flatten())
        #     pass

        # self.model.add(Dense(1))
        # self.model.add(Activation('sigmoid'))

        if model == "custom":
            self.custom = True
            self.model = load_model(model_path)
            #print(self.model.summary())
            #self.model.load_weights(model_path)
            self.max_dim = max_dim
            self.model_input = model_input
        else:
            self.custom = False
            self.cnnmodel = get_file(model, self.prebuilts_config[model]["model_path"])
            self.model = load_model(self.cnnmodel)
            self.max_dim = self.prebuilts_config[model]["max_dim"]
            self.model_input = self.prebuilts_config[model]["model_input"]



        self.fluor_fov = fluor_fov
        self.optional_fov = optional_fov


    def preprocess_image(self, image):

        h, w = image.shape

        max_h, max_w = self.max_dim, self.max_dim

        lines_to_add = max_h - h
        columns_to_add = max_w - w

        if lines_to_add > 0:
            if lines_to_add % 2 == 0:
                new_line = np.zeros((int(lines_to_add / 2), w))
                image = np.concatenate((new_line, image, new_line), axis=0)
            else:
                new_line_top = np.zeros((int(lines_to_add / 2) + 1, w))
                new_line_bot = np.zeros((int(lines_to_add / 2), w))
                image = np.concatenate((new_line_top, image, new_line_bot), axis=0)

        elif lines_to_add < 0:
            if (lines_to_add * -1) % 2 == 0:
                cutsize = int((lines_to_add * -1) / 2)
                image = image[cutsize:h - cutsize, :]
            else:
                cutsize = int((lines_to_add * -1) / 2)
                image = image[cutsize:h - cutsize - 1, :]

        if columns_to_add > 0:
            if columns_to_add % 2 == 0:
                columns_to_add = np.zeros((self.max_dim, int(columns_to_add / 2)))
                image = np.concatenate((columns_to_add, image, columns_to_add), axis=1)
            else:
                columns_to_add_left = np.zeros((self.max_dim, int(columns_to_add / 2) + 1))
                columns_to_add_right = np.zeros((self.max_dim, int(columns_to_add / 2)))
                image = np.concatenate((columns_to_add_left, image, columns_to_add_right), axis=1)

        elif columns_to_add < 0:
            if (columns_to_add * -1) % 2 == 0:
                cutsize = int((columns_to_add * -1) / 2)
                image = image[:, cutsize:w - cutsize]
            else:
                cutsize = int((columns_to_add * -1) / 2)
                image = image[:, cutsize:w - cutsize - 1]

        image = img_as_float(image)
        image = image.reshape(self.max_dim, self.max_dim, 1)

        return image

    def classify_cell(self, cell_object):
        
        x0, y0, x1, y1 = cell_object.box
        fluor = None
        optional = None

        if "Membrane" in self.model_input:
            fluor = rescale_intensity(img_as_float(self.fluor_fov[x0:x1 + 1, y0:y1 + 1] * cell_object.cell_mask))
            fluor_img = skresize(self.preprocess_image(fluor),
                             (100, 100),
                             order=0,
                             preserve_range=True,
                             anti_aliasing=False,
                             anti_aliasing_sigma=None)
        
        if "DNA" in self.model_input:
            optional = rescale_intensity(img_as_float(self.optional_fov[x0:x1 + 1, y0:y1 + 1] * cell_object.cell_mask))
            optional_img = skresize(self.preprocess_image(optional),
                                (100, 100),
                                order=0,
                                preserve_range=True,
                                anti_aliasing=False,
                                anti_aliasing_sigma=None)

        if self.model_input == "Membrane":
            pred = self.model.predict(fluor_img.reshape(-1, 100, 100, 1), verbose=0)
        elif self.model_input == "DNA":
            pred = self.model.predict(optional_img.reshape(-1, 100, 100, 1), verbose=0)
        elif self.model_input == "Membrane+DNA":    
            pred = self.model.predict(np.concatenate((fluor_img, optional_img), axis=1).reshape(-1, 100, 200, 1), verbose=0)

        if self.custom and len(pred[0])==1:
            return int(pred[0][0] > 0.5)+1
        else:
            return np.argmax(pred,axis=-1)[0] + 1
