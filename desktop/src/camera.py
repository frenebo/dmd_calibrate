import pycromanager
import numpy as np


def take_micromanager_pic_as_float_arr(core):
    core.snap_image()
    tagged_image = core.get_tagged_image()
    pixels = np.reshape(tagged_image.pix, newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])

    assert pixels.dtype == np.uint16, "Expecting the raw image from micromanager to be 16 bit integer format"



    return pixels
