
from matplotlib import pyplot as plt
import numpy as np

def best_fit_affine_transform(dmd_coords, camera_coords):
    dmd_coords = np.array(dmd_coords).astype(float)
    camera_coords = np.array(camera_coords).astype(float)
    
    # Make sure input data is correctly formatted
    assert dmd_coords.shape == camera_coords.shape, "dmd and camera coordinate arrays should have same shape"
    assert dmd_coords.shape[0] == 2, "coord arrays should be (2xN), instead got {}".format(dmd_coords.shape)
    
    # Make sure there is sufficient data to fit coordinates
    assert dmd_coords.shape[1] >= 3, "Cannot fit transformation with less than three pairs of points."

    N = dmd_coords.shape[1]

    # Add a row of ones
    dmd_coords = np.vstack( (dmd_coords, np.ones((1,N)) ) )


    # Change shape to Nx1 and Nx3 for linalg

    camera_coords_x = camera_coords[0][:,np.newaxis]
    camera_coords_y = camera_coords[1][:,np.newaxis]
    dmd_coords = np.swapaxes(dmd_coords, 0, 1)

    cam_coeffs_x = np.linalg.lstsq(dmd_coords, camera_coords_x, rcond=None)[0].T[0]
    cam_coeffs_y = np.linalg.lstsq(dmd_coords, camera_coords_y, rcond=None)[0].T[0]

    T = np.vstack( [cam_coeffs_x, cam_coeffs_y] )
    
    A = T[:,:2]
    b = T[:,2:3]

    return A,b

def transform_camera_to_dmd_image(desired_cam_image, cam_to_dmd_Tmat):
    raise NotImplementedError

