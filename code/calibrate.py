import numpy as np
import time
import cv2
from PIL import Image
import subprocess
import io

class Calibrator:
    def __init__(self):
        # Set up second display settings
        self.dmd_display_dims = (1280,800)
        self.first_display_dims = (1920,1080)

        self.image_save_path = "DMD_display_img_temp.jpg"
        self.running_feh = False

    def calibrate(self):
        # self.map_grid()

        width,height = self.dmd_display_dims
        i = 1
        while True:
            # print("Black")
            black_dmd_img = np.zeros((height,width),dtype=np.uint8)
            # self.display_image(black_dmd_img)

            # time.sleep(5)
            # # background_black = self.capture_blue_pixels()
            # # self.save_bw_floats(background_black,"black.jpg")

            print("White")
            self.display_image(np.ones_like(black_dmd_img)*np.iinfo(np.uint8).max)

            time.sleep(5)
            background_white = self.capture_blue_pixels()
            # self.save_bw_floats(background_white, "{}.jpg".format(i))
            i+=1
        self.stop_feh()

    def show_circle_at(self,x,y):
        dmd_w, dmd_h = self.dmd_display_dims
        if x < 10 or y < 10:
            raise Exception("cant show square at x < 5 or y < 5, not enough space")
        if x > dmd_w - 10 or y > dmd_h - 10:
            raise Exception("cant show square at x > {} or y > {}, not enough space".format(dmd_w-10,dmd_h-10))

        dmd_img = np.zeros((dmd_h,dmd_w),dtype=np.uint8)

        # Make a circle boolean mask
        xx,yy = np.mgrid[:20,:20]
        circle_mask = ((xx-9.5)**2+(yy-9.5)**2) < 91
        # "Color in" circle
        circle = np.zeros((20,20),dtype=np.uint8)
        circle[circle_mask] = np.iinfo(np.uint8).max

        # Place circle inside image
        dmd_img[x-10:x+10,y-10:y+10] = circle
        self.display_image(dmd_img)

    def save_bw_floats(self,float_img, fp):
        scaled_img = (float_img * np.iinfo(np.uint8).max).astype(np.uint8)
        # white_screen = (white_screen * np.iinfo(np.uint8).max).astype(np.uint8)
        Image.fromarray(scaled_img, "L").save(fp)


    def map_grid(self):
        width,height = self.dmd_display_dims

        black_dmd_img = np.zeros((height,width),dtype=np.uint8)
        self.display_image(black_dmd_img)

        background_black = self.capture_blue_pixels()
        self.save_bw_floats(background_black,"black.jpg")
        self.display_image(np.ones_like(black_dmd_img)*np.iinfo(np.uint8).max)
        background_white = self.capture_blue_pixels()
        self.save_bw_floats(background_white, "white.jpg")

        x_points = np.arange(50,width-49,100)
        y_points = np.arange(50,height-49,100)
        print("Mapping grid of {} by {} points".format(len(x_points), len(y_points)))

        blob_detector = cv2.SimpleBlobDetector()

        did_see = np.zeros((len(x_points),len(y_points)),dtype=int)

        for x_idx, dmd_x in enumerate(x_points):
            for y_idx, dmd_y in enumerate(y_points):
                print("Showing circle at {},{}".format(dmd_x,dmd_y))
                self.show_circle_at(dmd_x,dmd_y)
                circle_cam_img = self.capture_blue_pixels()

                # Normalize image from background
                circle_cam_img = circle_cam_img - background_black

                # Convert to uint8 array for cv2
                int_img = (circle_cam_img * np.iinfo(np.uint8).max).astype(np.uint8)
                int_img[circle_cam_img < 0] = 0
                int_img[circle_cam_img > 1] = np.iinfo(np.uint8).max
                circles = cv2.HoughCircles(int_img, cv2.HOUGH_GRADIENT,1,20)

                if circles is not None:
                    print("Circles shape:")
                    print(circles.shape)
                    circles = circles[0, :]

                    for (x, y, r) in circles:
                        print("Found circle at {x},{y} with radius {r}".format(x,y,r))

                    # # loop over the (x, y) coordinates and radius of the circles
                    # for (x, y, r) in circles:
                    #     # draw the circle in the output image, then draw a rectangle
                    #     # corresponding to the center of the circle
                    #     cv2.circle(output, (x, y), r, (0, 255, 0), 4)
                    #     cv2.rectangle(output, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)

                    did_see[x_idx,y_idx]=1

        print("Did see matrix:")
        print(did_see)


        # self.stop_feh()

    def display_image(self, image_arr):
        if self.running_feh:
            self.stop_feh()

        first_display_w, first_display_h = self.first_display_dims
        dmd_w, dmd_h = self.dmd_display_dims
        assert image_arr.shape == (dmd_h, dmd_w), "Image array should be 2D, dimensions (height,width)"

        Image.fromarray(image_arr, "L").save(self.image_save_path)


        subprocess.call("feh --geometry {width}x{height}+{xoffset}+{yoffset} --borderless {image} &".format(
            width=dmd_w,
            height=dmd_h,
            xoffset=first_display_w,
            yoffset=0,
            image=self.image_save_path
        ), shell=True)
        self.running_feh = True
        time.sleep(0.5)

    def stop_feh(self):
        if not self.running_feh:
            print("Warning: killing feh when it's not supposed to be running")

        subprocess.call("pkill feh", shell=True)
        self.running_feh = False

    def capture_blue_pixels(self):
        exposure_seconds = 0.2
        exposure_us = exposure_seconds*1000000
        temp_image_fp = "temp_raw.jpg"

        command = "raspistill -md 3 -awb off --awbgains -1.0,1.0 --shutter {} --analoggain 1.0 --digitalgain 1.0 --nopreview -r -o {}".format(
                exposure_us,
                temp_image_fp)
        print("Calling " + command)
        subprocess.call(command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True)
        print("Finished raspistill")

        # Got following from https://www.strollswithmydog.com/open-raspberry-pi-high-quality-camera-raw/#footnote

        # Read in the whole binary image tail of the
        # .jpg file with appended raw image data
        with open(temp_image_fp, 'rb') as filraw:
            filraw.seek(-18711040, io.SEEK_END)
            imbuf = filraw.read()
            if imbuf[:4] != b'BRCM':
                print('Binary data start tag BRCM was NOT found at this seek position')
                raise Exception("Couldn't find start tag for the camera raw bayer data. Was the jpeg captured with raw data at the end?")


        # subprocess.call("rm {}".format(temp_image_fp),shell=True)

        # Image data proper starts after 2^15 bytes = 32768
        imdata = np.frombuffer(imbuf, dtype=np.uint8)[32768:]
        # Reshape the data to 3056 rows of 6112 bytes each and crop to 3040 rows of 6084 bytes
        imdata = imdata.reshape((3056, 6112))[:3040, :6084]



        # Make an output 16 bit image
        im = np.zeros((3040, 4056), dtype=np.uint16)
        # Unpack the low-order bits from every 3rd byte in each row
        for byte in range(2):
            im[:, byte::2] = ( (imdata[:, byte::3] << 4) | ((imdata[:, 2::3] >> (byte * 4)) & 0b1111) )
        print("Image shape: {}".format(im.shape))
        print("Image average brightness: {}".format(np.mean(im)))
        print("Image highest brightness: {}".format(im.max()))
        # print("Image highest b")

        def crappyhist(a, bins=20, width=140):
            h, b = np.histogram(a, bins)

            for i in range (0, bins):
                print('{:12.5f}  | {:{width}s} {}'.format(
                    b[i],
                    '#'*int(width*h[i]/np.amax(h)),
                    h[i],
                    width=width))
            print('{:12.5f}  |'.format(b[bins]))

        crappyhist(im.flatten())
        # A_pix = im[::2,::2]
        # B_pix = im[1::2,::2]
        # C_pix = im[::2,1::2]
        # D_pix = im[1::2,1::2]
        # print("{} {}\n{} {}".format(np.mean(A_pix),np.mean(B_pix),np.mean(C_pix),np.mean(D_pix)))

        # blue_pixels = im[::2,::2]
        # float_arr = blue_pixels.astype(float)

        # pixels_overexposed = (blue_pixels >= 2**12 - 1).sum()
        # # percent
        # if pixels_overexposed != 0:
        #     print("WARNING: {} pixels are overexposed in blue!".format(pixels_overexposed))
        # print("Average blue pixel value: {}".format(blue_pixels.mean()))

        # # from 12 to 16 bit
        # float_arr /= (2**12 - 1)
        # float_arr[float_arr > 1] = 1
        # float_arr[float_arr < 0] = 0

        # return float_arr

        # raw_data = np.fromfile(temp_image_fp, dtype=np.uint8)
        # camera = RaspberryPiHqCamera(3, CFAPattern.BGGR)

        # imdata = imdata.astype(np.uint16)


        # r = RPICAM2DNG(camera)
        # unpacked_bayer = r.__unpack_pixels__(imdata)
        # print("Unpacked bayer:")
        # print(unpacked_bayer.shape)
        # print(unpacked_bayer.dtype)

        # raise NotImplementedError

    # def capture_blue_pixels(self):
    #     # perform capture
    #     stream = picamerax.array.PiBayerArray(self.camera)
    #     self.camera.capture(stream, "jpeg", bayer=True)
    #     print("Shutter speed was: ", self.camera.exposure_speed)
    #     # get raw Bayer data
    #     bayer_output_bggr = np.sum(stream.array, axis=2).astype(np.uint16)

    #     blue_pixels = bayer_output_bggr[::2,::2]
    #     float_arr = blue_pixels.astype(float)

    #     pixels_overexposed = (blue_pixels >= 2**12 - 1).sum()
    #     # percent
    #     if pixels_overexposed != 0:
    #         print("{} pixels are overexposed in blue.".format(pixels_overexposed))

    #     # from 12 to 16 bit
    #     float_arr /= (2**12 - 1)
    #     float_arr[float_arr > 1] = 1
    #     float_arr[float_arr < 0] = 0

    #     return float_arr

        # blue_pixels_normalized = ( float_arr * np.iinfo(np.uint16).max ).astype(np.uint16)

        # return blue_pixels_normalized



        # # demosaicing
        # rgb = cv2.cvtColor(output, cv2.COLOR_BayerRG2RGB)

        # if subtract_black_level:
        #     # subtract black level
        #     black_level = 256.3
        #     rgb = rgb - black_level

        # # white balance
        # rgb[:, :, 0] *= float(awb_gains[0])
        # rgb[:, :, 2] *= float(awb_gains[1])

        # # color correction
        # M = np.array(
        #     [
        #         [2.0659, -0.93119, -0.13421],
        #         [-0.11615, 1.5593, -0.44314],
        #         [0.073694, -0.4368, 1.3636],
        #     ]
        # )
        # rgb_flat = rgb.reshape(-1, 3, order="F")
        # rgb = (rgb_flat @ M.T).reshape(rgb.shape, order="F")

        # # clip
        # rgb = rgb / (2 ** n_bits - 1 - black_level)
        # rgb[rgb > 1] = 1
        # rgb[rgb < 0] = 0

        # output = ( rgb * np.iinfo(np.uint16).max ).astype(np.uint16)

        # return output
        # # output = (rgb * (2 ** n_bits - 1)).astype(np.uint16)

        # # save
        # # cv2.imwrite("test_bayer_corrected.png", cv2.cvtColor(output, cv2.COLOR_RGB2BGR))



    # def display_image(self, image_arr):
    #     w,h = image_arr.shape
    #     assert image_arr.dtype == np.uint8, "Image array type is uint8"
    #     assert w == self.slm_width, "Image width matches slm"
    #     assert h == self.slm_height, "Image width matches"

    #     core.set_slm_image(self.slm_name, image_arr.flatten())

if __name__ == "__main__":

    # pi_camera = picamerax.PiCamera()

    # with Bridge() as bridge:
    calibrator = Calibrator()
    try:
        calibrator.calibrate()
    except:
        if calibrator.running_feh:
            calibrator.stop_feh()
        raise
    if calibrator.running_feh:
        calibrator.stop_feh()
        # calibrate_display(bridge)


