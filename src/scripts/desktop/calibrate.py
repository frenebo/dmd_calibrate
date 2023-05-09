
import numpy as np
import tifffile
import pycromanager
import math
import os
import cv2
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.widgets import Button

from .raspiinterface import RaspiInterface
from .camera import take_micromanager_pic_as_float_arr
from .coordtransformations import best_fit_affine_transform


# When calibration doesn't work right
class CalibrationException(Exception):
    pass

def save_img_for_dmd(np_float_img, path):
    assert np_float_img.dtype == float, "Image should be float array"
    assert np.all(np_float_img >= 0), "Image should have no negative brightness values"
    assert np.all(np_float_img <= 1), "Image should have no brightness values greater than 1"
    assert np_float_img.shape == (DMD_H, DMD_W), "Numpy float image should have shape {}, instead received  {}".format((DMD_H, DMD_W), np_float_img.shape)

    max_int16 =  np.iinfo(np.uint16).max

    np_int8_img = (np_float_img *  max_int16 ).astype(np.uint16)


    tifffile.imwrite(path, np_int8_img)

def draw_white_circle(np_float_img, diameter, center_x, center_y):
    assert np_float_img.dtype == float, "Image should be float array"
    assert int(diameter) == diameter, "Diameter value should be integer"
    assert int(center_x) == center_x, "Center x value should be integer"
    assert int(center_y) == center_y, "Center y value should be integer"
    assert diameter > 0, "Diameter should be positive"
    assert diameter % 2 == 1, "Diameter should be odd, so the circle will be centered on a single pixel"

    diameter = int(diameter)
    center_x = int(center_x)
    center_y = int(center_y)

    circ_xx, circ_yy = np.meshgrid(np.arange(diameter), np.arange(diameter))

    # This should already be a whole number, but casting to an integer so we can array index with it
    rad = int((diameter - 1) / 2)

    circ_mask = (np.square(circ_xx - rad) + np.square(circ_yy - rad)) <= np.square(rad + 0.5)

    # Convert to float
    circ_mask  = circ_mask.astype(float)

    np_float_img[center_y - rad:center_y + rad + 1, center_x - rad:center_x + rad + 1] += circ_mask

    # If the spot wasn't already white, then it'll have brightness more than 1.0 now - fix this here
    np_float_img[np_float_img > 1.0] = 1.0

def show_black_white_calibration_images(white_photos, black_photos, white_level, black_level):
    hist_min = np.amin(
        np.array([white_photos, black_photos])
    )

    hist_max = np.amax(
        np.array([white_photos, black_photos])
    )

    fig, axs = plt.subplots(4,max(len(white_photos), len(black_photos)), figsize=(15,7), gridspec_kw={'height_ratios':[3,1,3,1]})
    for i in range(len(white_photos)):
        # Show image without ticks 
        axs[0][i].set_axis_off()
        img_ax = axs[0][i].imshow(white_photos[i], cmap='gray')
        
        counts, bins = np.histogram(
            white_photos[i].flatten(),
            bins=50,
            range=(hist_min, hist_max),
            )
        axs[1][i].stairs(counts, bins, fill=True, color='white')
        axs[1][i].set_facecolor('black')
        axs[1][i].tick_params(left=False,labelleft = False)
    
    axs[0][0].set_axis_on()
    axs[0][0].tick_params(labelleft = False,left=False,bottom=False,labelbottom=False)
    axs[0][0].set_ylabel("All White\nWhite Level={:.1f}".format(white_level))

    for i in range(len(black_photos)):
        axs[2][i].set_axis_off()
        img_ax = axs[2][i].imshow(black_photos[i], cmap='gray')

        counts, bins = np.histogram(
            black_photos[i].flatten(),
            bins=50,
            range=(hist_min, hist_max),
        )
        axs[3][i].stairs(counts, bins, fill=True, color='white')
        axs[3][i].set_facecolor('black')
        axs[3][i].tick_params(left=False, labelleft=False)
    
    axs[2][0].set_axis_on()
    axs[2][0].tick_params(labelleft = False,left=False,bottom=False,labelbottom=False)
    axs[2][0].set_ylabel("All Black\nBlack Level={:.1f}".format(black_level))
    
    plt.show()

def get_background_black_and_white_levels(core, raspi_controller, dmd_img_dir):
    # @TODO calibrate these values
    NUM_BLACK_SAMPLES = 10
    NUM_WHITE_SAMPLES = 10

    gaussian_blur_sigma = 201

    max_relative_variance_rel_to_b_w_diff = 0.1
    max_black_field_var_rel_to_b_w_diff = 0.1
    max_white_field_var_rel_to_b_w_diff = 0.1

    dmd_dims = (DMD_H, DMD_W)

    black_img_dmd = np.zeros( dmd_dims, dtype=float)
    black_img_dmd_path = os.path.join(dmd_img_dir, "allblack.tiff")
    save_img_for_dmd(black_img_dmd, black_img_dmd_path)
    raspi_controller.send_image_to_feh(black_img_dmd_path)

    black_photos = []

    for i in range(NUM_BLACK_SAMPLES):
        black_img_microphoto = take_micromanager_pic_as_float_arr(core)
        black_photos.append(black_img_microphoto)

    white_img_dmd = np.ones(dmd_dims, dtype=float)
    white_img_dmd_path = os.path.join(dmd_img_dir, "allwhite.tiff")
    save_img_for_dmd(white_img_dmd, white_img_dmd_path)
    raspi_controller.send_image_to_feh(white_img_dmd_path)

    white_photos = []
    for i in range(NUM_WHITE_SAMPLES):
        white_img_microphoto = take_micromanager_pic_as_float_arr(core)
        white_photos.append(white_img_microphoto)

    all_black_samples = np.array(black_photos)
    all_white_samples = np.array(white_photos)

    var_within_black = np.average(np.var(all_black_samples, axis=0))
    var_within_white = np.average(np.var(all_white_samples, axis=0))


    avg_black = np.average(all_black_samples, axis=0)
    avg_white = np.average(all_white_samples, axis=0)


    var_between_avg_black_and_white = np.average(np.var(np.array([avg_black, avg_white]), axis=0))

    # If the dmd lit-up area only covers part of the image, we need to find the white level based on the area that is white.
    # averaged_black_img_field = np.mean(all_black_samples)
    # averaged_white_img_field = np.mean(all_white_samples)
    mean_black_brightness = np.average(avg_black)
    mean_white_brightness = np.average(avg_white)
    
    blurred_black_avg = cv2.GaussianBlur(avg_black, (gaussian_blur_sigma, gaussian_blur_sigma), 0)
    blurred_white_avg = cv2.GaussianBlur(avg_white, (gaussian_blur_sigma, gaussian_blur_sigma), 0)

    # The pixels that are on average more bright in white than black images give us the mask for the part of the image
    # We use to find the white level. We use the blurred images to find this region so that speckles don't affect it too much
    illuminated_section_mask = blurred_white_avg > mean_black_brightness + (mean_white_brightness - mean_black_brightness) * 0.3
    print("mean black: ", mean_black_brightness)
    # print("mean white: ", mean_white_brightness)

    black_level = mean_black_brightness
    white_level = np.average(avg_white[illuminated_section_mask])


    print("white level: ", white_level)

    show_black_white_calibration_images(white_photos, black_photos, white_level, black_level)
    
    # Check that there is a statistical difference between datasets -
    # This should show whether there is a detected difference between
    # DMD "white screen" and "black screen"
    if (
        (var_within_black > max_relative_variance_rel_to_b_w_diff * var_between_avg_black_and_white) or
        (var_within_white > max_relative_variance_rel_to_b_w_diff * var_between_avg_black_and_white)
        ):
        raise CalibrationException("Variance among calibration images is high compared to variance between average black image and average white image. Var within black calibration images: {} within white calibration images: {}. Var between average black and average white image: {}. Is the DMD on? When displaying a white image, is the projected image overlapping the area captured by the camera sensor? Is the exposure time long enough?".format(
            var_within_black,
            var_within_white,
            var_between_avg_black_and_white,
        ))

    return black_level, white_level

def find_blobs_in_photo(np_float_img, black_level, white_level):
    print("Finding blobs in photo")
    gaussian_blur_sigma = 81
    touching_edge_pixels_threshold = 3

    # Areas closer to white than to black are considered white
    thresh = (black_level + white_level) / 2

    blurred = cv2.GaussianBlur(np_float_img, (gaussian_blur_sigma, gaussian_blur_sigma), 0)

    above_thresh = np.uint8(blurred > thresh)

    contours, hierarchy = cv2.findContours(above_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    found_blobs = []
    found_contours = []

    for contour_i in range(len(contours)):
        contour = contours[contour_i]
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour,True)

        if perimeter <= 0 or area <= 0:
            continue


        circularity = 2*np.sqrt(np.pi*area)  / perimeter

        x_min,y_min,width,height = cv2.boundingRect(contour)

        is_touching_edge = (
            (x_min <= touching_edge_pixels_threshold) or
            (y_min <= touching_edge_pixels_threshold) or
            (x_min + width >= np_float_img.shape[0] - touching_edge_pixels_threshold) or
            (y_min + height >= np_float_img.shape[1] - touching_edge_pixels_threshold)
            )

        M = cv2.moments(contour)

        cx = M["m10"]/M["m00"]
        cy = M["m01"]/M["m00"]


        found_blobs.append({
            "touching_edge": is_touching_edge,
            "circularity": circularity,
            "perimeter": perimeter,
            "area": area,
            "centroid_x": cx,
            "centroid_y": cy,
            "x_min": x_min,
            "y_min": y_min,
            "width": width,
            "height": height,
        })
        found_contours.append(contour)

    return found_blobs, found_contours

def analyze_calibration_measurements(calibration_measurements):
    dmd_circle_coords = []
    cam_circle_coords = []


    for datapt in calibration_measurements:
        dmd_circle_x = datapt["dmd_circle_x"]
        dmd_circle_y = datapt["dmd_circle_y"]
        blob = datapt["camera_detected_blob"]

        cam_circle_x = blob["centroid_x"]
        cam_circle_y = blob["centroid_y"]

        dmd_circle_coords.append([dmd_circle_x, dmd_circle_y])
        cam_circle_coords.append([cam_circle_x, cam_circle_y])

    dmd_circle_coords = np.array(dmd_circle_coords).T
    cam_circle_coords = np.array(cam_circle_coords).T

    T = best_fit_affine_transform(dmd_circle_coords, cam_circle_coords)

    return T

def show_calibration_pics(photo_arr, contours_arr, blobs_info_arr):
    # plt.clf()
    num_y = len(photo_arr)
    num_x = len(photo_arr[0])

    # The event handler for a legend-line being toggled 
    legendline_info = {}
    # An array where we put all of the blob lines for each calibration image - this way we can look at it and 
    # See which blobs have been toggled on/off
    blobline_arr =  [[[] for x in range(num_x)] for y in range(num_y)]
    crosshairs_arr = [[[] for x in range(num_x)] for y in range(num_y)]

    # Start off with all blobs selected
    selected_blob_indices = [[ [i for i in range(len(blobs_info_arr[y][x]))]  for x in range(num_x) ] for y in range(num_y)]

    # pics_have_one_or_zero_selected_blobs = [[False for x in range(num_x)] for y in range(num_y)]

    fig, axs = plt.subplots(num_y, num_x, figsize=(15,7))
    for row_idx in range(num_y):
        for col_idx in range(num_x):
            ax = axs[row_idx][col_idx]
            ax.set_axis_off()
            calib_pic = photo_arr[row_idx][col_idx]
            # calib_pic = Image.fromarray(np.)
            ax.imshow(calib_pic, cmap='gray')
            im_contours = contours_arr[row_idx][col_idx]
            for i, c in enumerate(im_contours):
                X,Y = np.array(c).T
                X=X[0]
                Y=Y[0]
                
                blob_line = ax.plot( X, Y , linewidth=2,alpha=0.8, label="blob {}".format(i))[0]
                blobline_arr[row_idx][col_idx].append(blob_line)

            lines = ax.get_lines()
            leg = ax.legend(bbox_to_anchor=(1.1,1), borderaxespad=0, loc="upper left")
            for legline, origline in zip(leg.get_lines(), lines):
                legline.set_picker(True)
                legendline_info[legline] = {
                    "origline": origline,
                    "row_idx": row_idx,
                    "col_idx": col_idx,
                }
    
    def update_calibration_image_crosshairs(row_idx, col_idx):
        num_visible = 0
        last_visible_blob_idx = None
        

        selected_blob_indices[row_idx][col_idx] = []
        for i, blobline in enumerate(blobline_arr[row_idx][col_idx]):
            if blobline.get_visible():
                num_visible += 1
                last_visible_blob_idx = i
                selected_blob_indices[row_idx][col_idx].append(i)
        # print(selected_blob_indices)

        

        ax = axs[row_idx][col_idx]
        old_crosshairs = crosshairs_arr[row_idx][col_idx]

        if len(old_crosshairs) != 0:
            for line in old_crosshairs:
                ax.lines.remove(line)

        #If there is only one visible blob, we plot crosshairs pointing to its center
        if num_visible == 1:
            blob_info = blobs_info_arr[row_idx][col_idx][last_visible_blob_idx]
            blob_x = blob_info["centroid_x"]
            blob_y = blob_info["centroid_y"]
            
            vline = ax.axvline(blob_x, color='yellow', linewidth=0.8, alpha=0.5)
            hline = ax.axhline(blob_y, color='yellow', linewidth=0.8, alpha=0.5)

            crosshairs_arr[row_idx][col_idx] = [vline, hline]
        else:
            crosshairs_arr[row_idx][col_idx] = []
        
        update_submit_button_get_new_cid_or_none()
    
    def on_pick(event):
        #On the pick event, find the original line corresponding to the legend
        #proxy line, and toggle its visibility.
        legline = event.artist
        origline = legendline_info[legline]["origline"]
        row_idx =  legendline_info[legline]["row_idx"]
        col_idx =  legendline_info[legline]["col_idx"]

        visible = not origline.get_visible()
        origline.set_visible(visible)
        #Change the alpha on the line in the legend so we can see what lines
        #have been toggled.
        legline.set_alpha(1.0 if visible else 0.2)

        # this determines whether there are crosshairs now
        update_calibration_image_crosshairs(row_idx, col_idx)

        fig.canvas.draw()
    
    submit_button_callback_cid = None
    
    submit_but_notready_text = "Each calibration image should only have 1 or 0 blobs selected before proceeding"

    # In this function, it checks whether every calibration image has its extra blob detections removed
    # If calibration blobs are ready, it enables the button, and adds the callback
    # If not ready, it disables, and removes the previous callback if it exists (we stored its cid in a variable)
    def update_submit_button_get_new_cid_or_none():
        nonlocal submit_button_callback_cid

        for y in range(num_y):
            for x in range(num_x):
                if len(selected_blob_indices[y][x]) > 1:
                    if submit_button_callback_cid is not None:
                        submit_but.label.set_text(submit_but_notready_text)
                        submit_but.disconnect(submit_button_callback_cid)
                        submit_button_callback_cid = None
                    return
        
        if submit_button_callback_cid is None:
            submit_but.label.set_text('Click to submit')
            submit_button_callback_cid = submit_but.on_clicked(close_graph)
    
    def close_graph(ev):
        plt.close('all')

    fig.canvas.mpl_connect('pick_event', on_pick)

    fig.suptitle(
        'Circles Detected\n'+
        'Click on the lines in legends to toggle blobs on/off in order to remove incorrect detections of blobs or bad data points\n'+
        'All extra blobs in a calibration image should be removed before continuing'
    )

    axnext = fig.add_axes([0.2, 0.05, 0.6, 0.065])

    submit_but = Button(axnext, submit_but_notready_text)
    
    for row_idx in range(num_y):
        for col_idx in range(num_x):        
            update_calibration_image_crosshairs(row_idx, col_idx)

    plt.show()

    # If user closes matplotlib window without narrowing down the choices of calibration detected blobs, we can't proceed
    if submit_button_callback_cid is None:
        raise Exception("Cannot close window without eliminating extra blobs from calibration images. Try again")
    
    return selected_blob_indices

def calibrate_geometry(core, raspi_controller, workdir):
    dmd_img_dir = os.path.join(workdir, "imgsfordmd")
    os.makedirs(dmd_img_dir, exist_ok=True)

    print("Finding background black and white brightness levels")
    black_level, white_level = get_background_black_and_white_levels(core, raspi_controller, dmd_img_dir)


    fit_transform_max_acceptable_camera_err = 10

    circle_diameter = 101
    edge_margin = math.ceil(circle_diameter / 2)

    grid_x_positions = np.arange(edge_margin, DMD_W - 1 - edge_margin, 300)
    grid_y_positions = np.arange(edge_margin, DMD_H - 1 - edge_margin, 300)

    num_y = len(grid_y_positions)
    num_x = len(grid_x_positions)

    photo_arr = []
    contours_arr = []
    blobs_info_arr = []



    for y_idx in range(num_y):
        row_photos = []
        row_contours = []
        row_blobs_info = []

        for x_idx in range(num_x):
            circle_dmd_x = grid_x_positions[x_idx]
            circle_dmd_y = grid_y_positions[y_idx]

            print("Showing calibration circle at x {}, y {} on dmd".format(circle_dmd_x, circle_dmd_y))
            marker_img_dmd = np.zeros( (DMD_H, DMD_W), dtype=float)

            draw_white_circle(marker_img_dmd, circle_diameter, circle_dmd_x, circle_dmd_y)

            circle_path = os.path.join(dmd_img_dir, "circle_calibration_marker.tiff")
            save_img_for_dmd(marker_img_dmd, circle_path)
            raspi_controller.send_image_to_feh(circle_path)

            circle_microphoto = take_micromanager_pic_as_float_arr(core)

            found_blobs, found_contours = find_blobs_in_photo(circle_microphoto, black_level, white_level)

            row_photos.append(circle_microphoto)
            row_contours.append(found_contours)
            row_blobs_info.append(found_blobs)

        photo_arr.append(row_photos)
        contours_arr.append(row_contours)
        blobs_info_arr.append(row_blobs_info)
    
    # 2D Array of which blobs 
    calibration_blob_selections = show_calibration_pics(photo_arr,  contours_arr, blobs_info_arr)
    print(calibration_blob_selections)

    selected_calibration_measurements = []
    for y_idx in range(num_y):
        for x_idx in range(num_x):
            circle_dmd_x = grid_x_positions[x_idx]
            circle_dmd_y = grid_y_positions[y_idx]

            for blob_idx in calibration_blob_selections[y_idx][x_idx]:
                selected_calibration_measurements.append({
                    "dmd_circle_x": circle_dmd_x,
                    "dmd_circle_y": circle_dmd_y,
                    "camera_detected_blob": blobs_info_arr[y_idx][x_idx][blob_idx],
                })

    transformT = analyze_calibration_measurements(selected_calibration_measurements)
    cam_dims = photo_arr[0][0].shape

    desired_cam_image = np.zeros( cam_dims, dtype=float)
    desired_cam_image[3*cam_dims[0]//8:5*cam_dims[0]//8, cam_dims[1]//4:3*cam_dims[1]//4] = 1.0






    img_to_show = cv2.warpAffine(desired_cam_image, transformT, (DMD_W, DMD_H), flags=cv2.WARP_INVERSE_MAP)
    test_img_path = os.path.join(dmd_img_dir, "circle_calibration_marker.tiff")
    save_img_for_dmd(img_to_show, test_img_path)
    raspi_controller.send_image_to_feh(test_img_path)
    input("enter any input to close program. You can check out the pattern in micromanager now")

# def calibrate(
#     hostname,
#     username,
#     password,
#     workdir):
#     os.makedirs(workdir, exist_ok=True)


#     with pycromanager.Bridge() as bridge:
#         core = bridge.get_core()
#         raspi_controller = RaspiInterface(hostname, username, password)

#         raspi_controller.start_feh()

#         try:
#             calibrate_geometry(core, raspi_controller, workdir)
#         except:
#             raspi_controller.kill_feh()
#             raise
#         raspi_controller.kill_feh()

