
from matplotlib import pyplot as plt
import numpy as np

def best_fit_affine_transform(dmd_coords, camera_coords):
    dmd_coords = np.array(dmd_coords)
    camera_coords = np.array(camera_coords)
    assert dmd_coords.shape == camera_coords.shape, "dmd and camera coordinate arrays should have same shape"

    assert dmd_coords.shape[0] == 2, "coord arrays should be (2xN)"

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

    return T

def transform_camera_to_dmd_image(desired_cam_image, cam_to_dmd_Tmat):
    pass



def test_transformation():
    # Create two subplots and unpack the output array immediately
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))

    points = np.array([
        (3, 3),
        (3, 10),
        (10,3),
        (10, 10),
        (3,5),
        (4,10),
        (3,8),
    ],  dtype=float).T

    A = np.array([
        [0.8,0.2],
        [-0.2,0.8],
    ], dtype=float)



    origX, origY =  points

    ax1.scatter(origX, origY, marker='.')
    ax1.set_xlim(0,15)
    ax1.set_ylim(0,15)
    ax2.set_xlim(0,15)
    ax2.set_ylim(0,15)

    b = np.array([1.0, 2.0])

    new_points = A @ points + b[:, None]

    new_points[0][0] += 1

    newX, newY = new_points

    fitT = best_fit_affine_transform(points, new_points)

    fitA = fitT[:,:2]
    fitb = fitT[:,2:3]
    # print("A:")
    # print(A)
    # print(fitA)
    # print("b:")
    # print(b)
    # print(fitb)

    predX, predY = fitA @ points + fitb[:, None]

    plt.scatter(origX, origY, color='b')
    plt.scatter(newX, newY, color='g')
    plt.scatter(predX, predY, color='r')
    plt.show()


if __name__ == "__main__":
    test_transformation()