import numpy as np
import time
import cv2
from PIL import Image
import subprocess
import io
import json

class DmdPicSender:
    def __init__(self):
        self.dmd_w = 1280
        self.dmd_h = 800

        self.first_display_dims = (1920,1080)

    def display_image(self, image_path):
        first_display_w, first_display_h = self.first_display_dims

        subprocess.call("feh --geometry {width}x{height}+{xoffset}+{yoffset} --borderless {image} &".format(
            width=dmd_w,
            height=dmd_h,
            xoffset=first_display_w,
            yoffset=0,
            image=image_path
        ), shell=True)

        time.sleep(0.1)

    def stop_display_image(self):
        subprocess.call("pkill feh", shell=True)

class CameraInterface:
    def __init__(self):
        pass

    def capture_blue_pixels(self):
        exposure_seconds = 0.1
        exposure_us = exposure_seconds*1000000
        temp_image_fp = "temp_raw.jpg"

        command = "raspistill -md 3 -awb off --awbgains -1.0,1.0 --shutter {} --analoggain 1.0 --digitalgain 1.0 --nopreview -r -o {}".format(
                exposure_us,
                temp_image_fp)
        # print("Calling " + command)
        subprocess.call(command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True)
        # print("Finished raspistill")

        # Got following from https://www.strollswithmydog.com/open-raspberry-pi-high-quality-camera-raw/#footnote

        # Read in the whole binary image tail of the
        # .jpg file with appended raw image data
        with open(temp_image_fp, 'rb') as filraw:
            filraw.seek(-18711040, io.SEEK_END)
            imbuf = filraw.read()
            if imbuf[:4] != b'BRCM':
                # print('Binary data start tag BRCM was NOT found at this seek position')
                raise Exception("Couldn't find start tag for the camera raw bayer data. Was the jpeg captured with raw data at the end?")


        # subprocess.call("rm {}".format(temp_image_fp),shell=True)

        # Image data proper starts after 2^15 bytes = 32768
        imdata = np.frombuffer(imbuf, dtype=np.uint8)[32768:]
        # Reshape the data to 3056 rows of 6112 bytes each and crop to 3040 rows of 6084 bytes
        imdata = imdata.reshape((3056, 6112))[:3040, :6084]

        # Convert to 16 bit data
        imdata = imdata.astype(np.uint16)

        # Make an output 16 bit image
        im = np.zeros((3040, 4056), dtype=np.uint16)
        # Unpack the low-order bits from every 3rd byte in each row
        for byte in range(2):
            # im[:, byte::2] = (imdata[:, byte::3] <> (byte * 4)) & 0b1111)
            # for byte in range(2):]
            im[:, byte::2] = ( (imdata[:, byte::3] << 4) | ((imdata[:, 2::3] >> (byte * 4)) & 0b1111) )
        # print("Image shape: {}".format(im.shape))
        # print("Image average brightness: {}".format(np.mean(im)))
        # print("Image highest brightness: {}".format(im.max()))
        # # print("Image highest b")

        # def crappyhist(a, bins=20, width=80):
        #     h, b = np.histogram(a, bins)

        #     for i in range (0, bins):
        #         print('{:12.5f}  | {:{width}s} {}'.format(
        #             b[i],
        #             '#'*int(width*h[i]/np.amax(h)),
        #             h[i],
        #             width=width))
        #     print('{:12.5f}  |'.format(b[bins]))

        # crappyhist(im.flatten())
        A_pix = im[::2,::2]
        # B_pix = im[1::2,::2]
        # C_pix = im[::2,1::2]
        # D_pix = im[1::2,1::2]
        # print("{} {}\n{} {}".format(np.mean(A_pix),np.mean(B_pix),np.mean(C_pix),np.mean(D_pix)))

        blue_pixels = im[::2,::2]
        float_arr = blue_pixels.astype(float)

        pixels_overexposed = (blue_pixels >= 2**12 - 1).sum()
        # # percent
        # if pixels_overexposed != 0:
        #     print("WARNING: {} pixels are overexposed in blue!".format(pixels_overexposed))
        # print("Average blue pixel value: {}".format(blue_pixels.mean()))

        # from 12 bit
        float_arr /= (2**12 - 1)
        float_arr[float_arr > 1] = 1
        float_arr[float_arr < 0] = 0

        return float_arr

        # raw_data = np.fromfile(temp_image_fp, dtype=np.uint8)
        # camera = RaspberryPiHqCamera(3, CFAPattern.BGGR)

        # imdata = imdata.astype(np.uint16)


        # r = RPICAM2DNG(camera)
        # unpacked_bayer = r.__unpack_pixels__(imdata)
        # print("Unpacked bayer:")
        # print(unpacked_bayer.shape)
        # print(unpacked_bayer.dtype)

        # raise NotImplementedError


class Interface:
    def __init__(self):
        # self.camera_interface = CameraInterface()
        self.dmd_pic_sender = DmdPicSender()

    def input_loop(self):
        line = input()
        try:
            instruction = json.loads(line)
        except ValueError:
            output = {"type": "error", "reason": "Cannot parse input line as JSON"}
            print(json.dumps(output))
            return

        if "command" not in instruction:
            output = {"type": "error", "reason": "Input should be json with 'command' attribute"}
            print(json.dumps(output))
            return

        command = instruction["command"]
        if command == "takepicture":
            output = {"type": "error", "reason": "Camera not supported right now"}
            # if "savepath" not in instruction:
            #     output = {"type": "error", "reason": "Input should contain 'savepath' attribute for path to save picture on raspberry pi"}
            #     print(json.dumps(output))
            #     return

            # save_path = instruction["savepath"]
            # try:
            #     float_array_img = self.camera_interface.capture_blue_pixels()
            # except Exception as e:
            #     output = {"type": "error", "reason": str(e)}
            # self.save_bw_floats(float_array_img, save_path)

            # output = {"type": "success"}
            # print(json.dumps(output))
        elif command == "dmd_start_show_image":
            if "loadpath" not in instruction:
                output = {"type": "error", "reason": "Input should contain 'loadpath' attribute for path to load image for showing on DMD."}
                print(json.dumps(output))
                return

            loadpath = instruction["loadpath"]

            # Test image to see if valid grayscale image with right dimensions

            pil_img = Image.open(path)
            # grayscale
            pil_img = pil_img.convert('L')
            np_img = np.array(pil_img)
            # 0 to 1
            float_img = np_img / np.iinfo(np_img.dtype).max
            # 0 to 255
            int8_img = (float_img * np.iinfo(np.uint8).max).astype(np.uint8)

            desired_dims = (self.dmd_h, self.dmd_w)
            if int8_img.shape != desired_dims:
                output = {
                    "type": "error",
                    "reason": "Can't show image with shape {}, should be {}. Is the image grayscale jpeg and the right dimensions?".format(
                        int8_img.shape, desired_dims
                    ),
                }
                print(json.dumps(output))
                return

            self.dmd_pic_sender.display_image(int8_img)

            output = {"type": "success"}
            print(json.dumps(output))
            return
        elif command == "dmd_kill_show_image":
            self.dmd_pic_sender.stop_display_image()
            output = {"type": "success"}
            print(json.dumps(output))
            return

        else:
            output = {"error", "reason": "Unknown value for 'command' attribute"}
            print(json.dumps(output))
            return


    def save_bw_floats(self,float_img, fp):
        scaled_img = (float_img * np.iinfo(np.uint8).max).astype(np.uint8)
        # white_screen = (white_screen * np.iinfo(np.uint8).max).astype(np.uint8)
        Image.fromarray(scaled_img, "L").save(fp)




if __name__ == "__main__":
    interface = Interface()
    interface.input_loop()
