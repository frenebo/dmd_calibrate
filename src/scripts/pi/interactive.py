import numpy as np
import time
from PIL import Image
import subprocess
import json
from ..constants import DMD_W, DMD_H


# @TODO Find from Raspberry Pi software what the first display dimensions are?
class DmdPicSender:
    def __init__(self, first_display_dims):
        self.first_display_dims = first_display_dims

    def display_image(self, image_path):
        first_display_w, first_display_h = self.first_display_dims

        subprocess.call("feh --hide-pointer --geometry {width}x{height}+{xoffset}+{yoffset} --borderless {image} &".format(
            width=DMD_W,
            height=DMD_H,
            xoffset=first_display_w,
            yoffset=0,
            image=image_path
        ), shell=True)

        time.sleep(0.1)

    def stop_display_image(self):
        subprocess.call("pkill feh", shell=True)

class Interface:
    def __init__(self):
        first_display_dims = (1920,1080)

        self.dmd_pic_sender = DmdPicSender(first_display_dims)

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
        if command == "dmd_start_show_image":
            if "loadpath" not in instruction:
                output = {"type": "error", "reason": "Input should contain 'loadpath' attribute for path to load image for showing on DMD."}
                print(json.dumps(output))
                return

            loadpath = instruction["loadpath"]

            # Test image to see if valid grayscale image with right dimensions

            pil_img = Image.open(loadpath)
            # grayscale
            pil_img = pil_img.convert('L')
            np_img = np.array(pil_img)
            # 0 to 1
            float_img = np_img / np.iinfo(np_img.dtype).max
            # 0 to 255
            int8_img = (float_img * np.iinfo(np.uint8).max).astype(np.uint8)

            desired_dims = (DMD_H, DMD_W)
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
            output = {"type":"error", "reason": "Unknown value for 'command' attribute"}
            print(json.dumps(output))
            return


    def save_bw_floats(self,float_img, fp):
        scaled_img = (float_img * np.iinfo(np.uint8).max).astype(np.uint8)
        # white_screen = (white_screen * np.iinfo(np.uint8).max).astype(np.uint8)
        Image.fromarray(scaled_img, "L").save(fp)




