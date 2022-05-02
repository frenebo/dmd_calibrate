import numpy as np
from time import sleep
import picamerax
import picamerax.array
import cv2
from PIL import Image
import subprocess

# def read_camera():
#     return black_and_white_image

# def display_image(core, slm_name, np_arr):
#     core.set_slm_image(slm_name, np_arr.flatten())
#     core.display_slm_image(slm_name)

# def calibrate_display():
#     with Bridge() as bridge:
#         core = bridge.get_core()
#         slm_name = core.get_slm_device()

#         width = core.get_slm_width(slm_name)
#         height = core.get_slm_height(slm_name)

#         image_2d = np.zeros((height,width), dtype=np.uint8)
#         image_2d[0:height//2,0:width//2] = 255
#         display_image(core, slm_name, image_2d)

class Calibrator:
    def __init__(self, camera):
        # Set up camera
        # awb_gains = camera.awb_gains
        # print("AWB gains: {}", awb_gains)

        # camera.awb_mode = "off"
        # camera.awb_gains = awb_gains
        # camera.iso=100
        camera.framerate=1
        # camera.shutter_speed= 1000*1000
        # print("Exposure speed: ", camera.exposure_speed)

        # Set ISO to the desired value
        camera.iso = 100
        # Wait for the automatic gain control to settle
        # sleep(5)
        # Now fix the values
        camera.shutter_speed = 900000
        # camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = 'off'
        g = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = g
        # print("AWB gains:",g)
        # # Finally, take several photos with the fixed settings
        # camera.capture_sequence(['image%02d.jpg' % i for i in range(10)])

        self.camera = camera



        # Set up second display settings
        self.dmd_display_dims = (1280,800)
        self.first_display_dims = (1920,1080)

        self.image_save_path = "display_img_temp.jpg"
        self.running_feh = False
        # Set up DMD

        # self.core = bridge.get_core()
        # self.slm_name = self.core.get_slm_device()

        # self.slm_width = self.core.get_slm_width(self.slm_name)
        # self.slm_height = self.core.get_slm_height(self.slm_name)

    def calibrate(self):
        self.map_grid()

    def map_grid(self):
        self.blank_display()
        background = self.capture_blue_pixels()
        print("Average brightness: {}".format(np.mean(background)))
        print("Max brightness: {}".format(np.max(background)))
        print("Min brightness: {}".format(np.min(background)))
        background -= np.min(background)
        background /= np.max(background)
        background = (background * np.iinfo(np.uint8).max).astype(np.uint8)


        Image.fromarray(background, "L").save("blue_pixels.jpg")

        self.stop_feh()

    def blank_display(self):
        width,height = self.dmd_display_dims
        image_2d = np.zeros((height,width),dtype=np.uint8)
        self.display_image(image_2d)
        # print("Unimplemented")
        # # image_2d = np.zeros((self.slm_height, self.slm_width), dtype=np.uint8)
        # # self.display_image(image_2d)

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

    def stop_feh():
        if not self.running_feh:
            print("Warning: killing feh when it's not supposed to be running")

        subprocess.call("pkill feh", shell=True)
        self.running_feh = False

    def capture_blue_pixels(self):
        # perform capture
        stream = picamerax.array.PiBayerArray(self.camera)
        self.camera.capture(stream, "jpeg", bayer=True)
        print("Shutter speed was: ", self.camera.exposure_speed)
        # get raw Bayer data
        bayer_output_bggr = np.sum(stream.array, axis=2).astype(np.uint16)

        blue_pixels = bayer_output_bggr[::2,::2]
        float_arr = blue_pixels.astype(float)

        pixels_overexposed = (blue_pixels >= 2**12 - 1).sum()
        # percent
        if pixels_overexposed != 0:
            print("{} pixels are overexposed in blue.".format(pixels_overexposed))

        # from 12 to 16 bit
        float_arr /= (2**12 - 1)
        float_arr[float_arr > 1] = 1
        float_arr[float_arr < 0] = 0

        return float_arr

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

    pi_camera = picamerax.PiCamera()

    # with Bridge() as bridge:
    calibrator = Calibrator(pi_camera)
    try:
        calibrator.calibrate()
    except:
        pass
    if calibrator.running_feh:
        calibrator.stop_feh()
        # calibrate_display(bridge)


