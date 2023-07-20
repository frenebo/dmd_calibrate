import pytest
import numpy as np
from matplotlib import pyplot as plt

from ...scripts.utilities.coordtransformations import best_fit_affine_transform

class Test_best_fit_affine_transform():
    def test_dmd_coords_incorrect_shape(self):
        with pytest.raises(Exception):
            best_fit_affine_transform(
                np.zeros((3,6)),
                np.zeros((2,6)),
            )
    
    def test_cam_coords_incorrect_shape(self):
        with pytest.raises(Exception):
            best_fit_affine_transform(
                np.zeros((3,6)),
                np.zeros((2,6)),
            )
    
    def test_with_insufficient_coord_data(self):
        # should not perform affine transform fit with less than three pairs of coordinates
        with pytest.raises(Exception):
            best_fit_affine_transform(
                np.zeros(2, 2),
                np.zeros(2, 2),
            )
    
    def test_properly_fits_coords(self):
        dmd_pts = np.array([
            (3, 3),
            (3, 10),
            (10,3),
            (10, 10),
            (3,5),
            (4,10),
            (3,8),
        ],  dtype=float).T

        realA = np.array([
            [0.8,0.2],
            [-0.2,0.8],
        ], dtype=float)
        realb = np.array([1.0, 2.0])

        dmdX, dmdY =  dmd_pts

        cam_pts = realA @ dmd_pts + realb[:, None]
        # Add "noise" to measurement, so the affine transformation fit cannot be perfect
        cam_pts[0][0] += 0.1
        
        camX, camY = cam_pts
        
        fitA, fitb = best_fit_affine_transform(dmd_pts, cam_pts)
        
        predCamPts = fitA @ dmd_pts + fitb
        predCamX, predCamY = predCamPts
        # print(np.abs(predCamPts - cam_pts))
        
        # Make sure the camera coordinates predicted by the model match the "real" data well enough
        
        assert np.all( np.abs(predCamPts - cam_pts) < 0.1 )




#     fitT = best_fit_affine_transform(points, new_points)

#     fitA = fitT[:,:2]
#     fitb = fitT[:,2:3]

#     predX, predY = fitA @ points + fitb[:, None]

#     plt.scatter(origX, origY, color='b')
#     plt.scatter(newX, newY, color='g')
#     plt.scatter(predX, predY, color='r')
#     plt.show()



# def test_best_fit_affine_transform():
#     assert 0 == 0