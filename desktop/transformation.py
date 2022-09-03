
from matplotlib import pyplot as plt
import numpy as np

def test_transformation():
    # Create two subplots and unpack the output array immediately
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))

    points = np.array([
        (3, 3),
        (3, 10),
        (10,3),
        (10, 10),
    ],  dtype=float)
    origX, origY =  points.T
    # print(origX)
    # print(origY)
    ax1.scatter(origX, origY, marker='.')
    ax1.set_xlim(0,15)
    ax1.set_ylim(0,15)
    ax2.set_xlim(0,15)
    ax2.set_ylim(0,15)

    A = np.array([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
    ], dtype=float)

    dvec = np.array([0, 0, 1], dtype=float)

    points_3d = np.zeros((points.shape[0], 3),  dtype=float)
    points_3d[:, :2] = points
    # print(points_3d.T.shape)
    # print(A.shape)
    X_w = A @ points_3d.T + dvec[:, None]
    X_w = X_w.T

    # "Camera plane" distance from origin
    f = 1

    print(points_3d)
    print(X_w)
    X_w_zvals = X_w[:,2]
    x_c = f * X_w / X_w_zvals[:,None]
    print(x_c)

    new_points = x_c[:,:2]
    print(new_points)

    newX, newY = new_points.T

    ax2.scatter(newX, newY, marker='.')

    plt.show()


if __name__ == "__main__":
    test_transformation()