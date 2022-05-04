import numpy as np
from time import sleep
# import picamerax
# import picamerax.array
import cv2
from PIL import Image
import subprocess
from pidng.core import RPICAM2DNG
from pidng.camdefs import RaspberryPiHqCamera, CFAPattern

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
    def __init__(self):
        # # Set up camera
        # # awb_gains = camera.awb_gains
        # # print("AWB gains: {}", awb_gains)

        # # camera.awb_mode = "off"
        # # camera.awb_gains = awb_gains
        # # camera.iso=100
        # camera.framerate=1
        # # camera.shutter_speed= 1000*1000
        # # print("Exposure speed: ", camera.exposure_speed)

        # # Set ISO to the desired value
        # camera.exposure_mode = 'off'
        # camera.iso = 100
        # # Wait for the automatic gain control to settle
        # # sleep(5)
        # # Now fix the values
        # camera.shutter_speed = 900000
        # # camera.shutter_speed = camera.exposure_speed
        # # g = camera.awb_gains
        # camera.awb_mode = 'off'
        # # camera.awb_gains = g
        # # print("AWB gains:",g)
        # # # Finally, take several photos with the fixed settings
        # # camera.capture_sequence(['image%02d.jpg' % i for i in range(10)])

        # self.camera = camera



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

    def show_square_at(self,x,y):
        # if x
        # dmd_img = np.zeros((self))
        dmd_w, dmd_h = self.dmd_display_dims
        if x < 5 or y < 5:
            raise Exception("cant show square at x < 5 or y < 5, not enough space")
        if x > dmd_w - 5 or y > dmd_h - 5:
            raise Exception("cant show square at x > {} or y > {}, not enough space".format(dmd_w-5,dmd_h-5))

        dmd_img = np.zeros((dmd_h,dmd_w),dtype=np.uint8)

        # Fill in square
        dmd_img[x-5:x+5,y-5:y+5] = np.iinfo(np.uint8).max
        self.display_image(dmd_img)

    def map_grid(self):
        width,height = self.dmd_display_dims

        black_dmd_img = np.zeros((height,width),dtype=np.uint8)
        self.display_image(black_dmd_img)
        background_image = self.capture_blue_pixels()

        # white_dmd_img = np.full((height,width),np.iinfo(np.uint8).max,dtype=np.uint8)
        # self.display_image(white_dmd_img)
        # white_screen = self.capture_blue_pixels()

        # # point_num = width//
        # if width < 100:
        #     raise Exception("dmd not wide enough to display grid")
        # if height < 100:
        #     raise Exception("dmd not high enough to display grid")
        # x_points = np.arange(50,width-49,100)
        # y_points = np.arange(50,height-49,100)
        # # grid_x_mesh, grid_y = np.meshgrid(x_points, y_points)
        # # for
        for x_pt in x_points:
            for y_pt in y_points:
                self.white_square_image(x_pt,y_pt,20,width,height)
                self.capture_blue_pixels()

                break
            break
        # x_points = np.linspace()
        # white_screen = self.float_to_
        # white_screen = (white_screen * np.iinfo(np.uint8).max).astype(np.uint8)
        # Image.fromarray(white_screen, "L").save("white_screen.jpg")
        # print("Average brightness: {}".format(np.mean(background)))
        # print("Max brightness: {}".format(np.max(background)))
        # print("Min brightness: {}".format(np.min(background)))
        # background -= np.min(background)
        # background /= np.max(background)
        # background = (background * np.iinfo(np.uint8).max).astype(np.uint8)



        self.stop_feh()

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

    def stop_feh(self):
        if not self.running_feh:
            print("Warning: killing feh when it's not supposed to be running")

        subprocess.call("pkill feh", shell=True)
        self.running_feh = False

    def capture_blue_pixels(self):
        exposure_seconds = 2
        exposure_us = exposure_seconds*1000000
        temp_image_fp = "temp_raw.jpg"
        print("CALLING RASPISTILL")
        subprocess.call("raspistill -md 3 -ex off -awb off -ag 1 -dg 1 -awbg -1.0,1.0 -set -v -ss {} --nopreview -r -o {}".format(exposure_us, temp_image_fp), shell=True)
        print("FINISSHD RASPITSILL")
        raw_data = np.fromfile(temp_image_fp, dtype=np.uint8)
        camera = RaspberryPiHqCamera(3, CFAPattern.BGGR)
        r = RPICAM2DNG(camera)
        unpacked_bayer = r.__unpack_pixels__(raw_data)
        print("Unpacked bayer:")
        print(unpacked_bayer.shape)
        print(unpacked_bayer.dtype)

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


