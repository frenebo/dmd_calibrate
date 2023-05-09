import pycromanager
import numpy as np
import random
import math
from skimage.draw import polygon

class PycroConnectionError(Exception):
    pass

class StandInPycroInterface:
    def __init__(self):
        self.cam_h = 2000
        self.cam_w = 1500
        # self.dims = (2000, 2000)
        self.field_skew_radians = np.random.uniform(low=-0.05,high=0.05)
        self.field_h = self.cam_h * 0.7
        self.field_w = self.cam_w * 0.7
        self.field_center_y = self.cam_h / 2
        self.field_center_x = self.cam_w / 2

        self.bright_level = 2000
        self.dark_level = 100

        self.pretend_image = None
        pass
    
    def make_field_mask(self):
        center_to_corner_d = (1/2) * np.sqrt(self.field_w ** 2 + self.field_h ** 2)
        center_to_corner_angle = np.arctan(self.field_h / self.field_w)
        skew = self.field_skew_radians * np.random.uniform(0.95, 1.05)

        cent_x = self.field_center_x * np.random.uniform(0.99, 1.01)
        cent_y = self.field_center_y * np.random.uniform(0.99, 1.01)
        
        corn_angles = [
            center_to_corner_angle + skew,
            math.pi - center_to_corner_angle + skew,
            math.pi + center_to_corner_angle + skew,
            2 * math.pi - center_to_corner_angle + skew,
        ]

        vertices = []
        for corn_ang in corn_angles:
            x = cent_x + center_to_corner_d * math.cos(corn_ang)
            y = cent_y + center_to_corner_d * math.sin(corn_ang)
            vertices.append([x,y])
        vertices = np.array(vertices)
    


        mask = np.zeros((self.cam_w, self.cam_h), 'uint8')
        rr, cc = polygon(vertices[:,0], vertices[:,1], mask.shape)
        mask[rr,cc] = 1

        return mask
    
    def generate_background_noise(self):
        gauss = np.random.uniform(0,100, (self.cam_w, self.cam_h))
        return gauss
        # gauss = gauss.reshape(img.shape[0],img.shape[1],img.shape[2]).astype('uint8')
    
    def snap_pic(self):
        # dat = np.zeros(self.dims, dtype=np.uint16)

        bg_noise_image = self.generate_background_noise()

        if self.pretend_image is None:
            im =  self.generate_background_noise()
        elif self.pretend_image == "solid white":
            print("Making placeholder solid bright field image")
            im = self.make_field_mask().astype(float) * self.bright_level
            im += self.generate_background_noise()
            # return im
        elif self.pretend_image == "solid black":
            print("Making placeholder solid dark field image")
            im = self.make_field_mask().astype(float) * self.dark_level
            im += self.generate_background_noise()
        else:
            raise Exception("Unknown pretend image type '{}'".format(self.pretend_image))
        
        im = im.astype(np.uint16)
        return im

        # mask = self.make_field_mask()

        # return dat
    
    def standin_pretend_solid_white(self):
        self.pretend_image = "solid white"
        # self.pretend
    
    def standin_pretend_solid_black(self):
        self.pretend_image = "solid black"
        
    
    
    def set_imaging_settings_for_acquisition(
        self,
        auto_shutter=True,
        binning="1x1",
        multishutter_preset="LightEngineOnly",
        sapphire_on_override="off",
        sapphire_setpoint="10",
        exposure_ms=10,
    ):
        pass
    # def check_camera_res

class PycroInterface:
    filt_group_presets = ["000", "060", "120", "180", "240", "300"]
    lightengine_group_presets = ["Off", "OnHalf", "OnFull"]
    multishutter_group_presets = ["LightEngineOnly", "LaserOnly", "LightEngineAndLaser", "NoMembers"]
    sapphire_group_presets = ["10to110"]
    sapphire_on_override_group_presets = ["on", "off"]
    sapphire_power_setpoint_group_presets = ["10", "60", "110"]
    
    def __init__(self):
        try:
            self.core = pycromanager.Core()
        except Exception as e:
            raise PycroConnectionError(str(e))
        
        self.check_configuration_groups()

        self.camera_device_name = self.core.get_camera_device()

        # print(self.check_camera_res())

        # # print(self.core.get_current_pixel_size_config())
        # # print('asdf')
    
    def snap_pic(self):
        self.core.snap_image()
        tagged_image = self.core.get_tagged_image()
        pixels = np.reshape(tagged_image.pix, newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])

        assert pixels.dtype == np.uint16, "Expecting the raw image from micromanager to be 16 bit integer format"

        # pixels = pixels.astype(float)
        return pixels
    
    def check_camera_res(self):
        prev_auto_shutter = self.core.get_auto_shutter()
        self.core.set_auto_shutter(False)
        self.core.snap_image()
        tagged_image = self.core.get_tagged_image()
        self.core.set_auto_shutter(prev_auto_shutter)

        
        return {
            "h": tagged_image.tags["Height"],
            "w": tagged_image.tags["Width"],
            "dtype": tagged_image.pix.dtype,
        }
    
    def set_imaging_settings_for_acquisition(
        self,
        auto_shutter=True,
        binning="1x1",
        multishutter_preset="LightEngineOnly",
        sapphire_on_override="off",
        sapphire_setpoint="10",
        exposure_ms=10,
    ):
        if multishutter_preset not in self.multishutter_group_presets:
            raise Exception("Invalid MultiShutterMembers preset '{}': must be from list '{}'".format(multishutter_preset, self.multishutter_group_presets))
        if sapphire_on_override not in self.sapphire_on_override_group_presets:
            raise Exception("Invalid SapphireOnOverride preset '{}': must be from list '{}'".format(sapphire_on_override, self.sapphire_on_override_group_presets))
        if sapphire_setpoint not in self.sapphire_power_setpoint_group_presets:
            raise Exception("Invalid SapphirePowerSetpoint preset '{}': must be from list '{}'".format(sapphire_setpoint, self.sapphire_power_setpoint_group_presets))
        

        self.core.set_auto_shutter(auto_shutter)
        self.core.set_shutter_device("Multi Shutter")
        self.core.set_property(self.camera_device_name, "Binning", binning)
        self.core.set_config("SapphireOnOverride", sapphire_on_override)
        self.core.set_config("MultiShutterMembers", multishutter_preset)
        self.core.set_exposure(exposure_ms)

        print("Set imaging settings")

        
    def check_configuration_groups(self):
        java_conf_names = self.core.get_available_config_groups()
        conf_names = [java_conf_names.get(i) for i in range(java_conf_names.size())]
        print("Configuration groups: {}".format(str(conf_names)))

        expected_names = [
            "FilterWheel",
            "LightEnginePower",
            "MultiShutterMembers",
            "SapphireMinAndMaxPower",
            "SapphireOnOverride",
            "SapphirePowerSetpoint",
            ]
        
        for exp_name in expected_names:
            if exp_name not in conf_names:
                raise PycroConnectionError("Missing config group '{}', could not find in Micromanager".format(exp_name))
        

        java_filt_settings = self.core.get_available_configs("FilterWheel")
        mm_filt_wheel_settings = [java_filt_settings.get(i) for i in range(java_filt_settings.size())]

        
        for f_set in self.filt_group_presets:
            if f_set not in mm_filt_wheel_settings:
                raise PycroConnectionError("Micromanager is missing filter wheel setting '{}'".format(f_set))
        
        
        java_lightengine_sets = self.core.get_available_configs("LightEnginePower")
        mm_lightengine_sets = [java_lightengine_sets.get(i) for i in range(java_lightengine_sets.size())]

        
        for l_set in self.lightengine_group_presets:
            if l_set not in mm_lightengine_sets:
                raise PycroConnectionError("Micromanager is missing light engine setting '{}'".format(l_set))
        

        java_multishutter_sets = self.core.get_available_configs("MultiShutterMembers")
        mm_multishutter_settings = [java_multishutter_sets.get(i) for i in range(java_multishutter_sets.size())]

        
        for m_set in self.multishutter_group_presets:
            if m_set not in mm_multishutter_settings:
                raise PycroConnectionError("Micromanager is missing multishutter group setting '{}'".format(m_set))
        

        java_sapphire_minmax_sets = self.core.get_available_configs("SapphireMinAndMaxPower")
        mm_sapphire_minmax_sets = [java_sapphire_minmax_sets.get(i) for i in range(java_sapphire_minmax_sets.size())]
        
        
        for s_set in self.sapphire_group_presets:
            if s_set not in mm_sapphire_minmax_sets:
                raise PycroConnectionError("Micromanager is missing SapphireMinAndMaxPower group setting '{}'".format(s_set))
        

        java_sapphire_on_override = self.core.get_available_configs("SapphireOnOverride")
        mm_sapphire_on_override_sets = [java_sapphire_on_override.get(i) for i in range(java_sapphire_on_override.size())]

        
        for s_on_set in self.sapphire_on_override_group_presets:
            if s_on_set not in mm_sapphire_on_override_sets:
                raise PycroConnectionError("Micromanager is missing SapphireOnOverride setting '{}'".format(s_on_set))
        

        java_sapphire_power_setpoint_sets = self.core.get_available_configs("SapphirePowerSetpoint")
        mm_sapphire_power_setpoint_sets = [java_sapphire_power_setpoint_sets.get(i) for i in range(java_sapphire_power_setpoint_sets.size())]
        
        
        for s_power_set in self.sapphire_power_setpoint_group_presets:
            if s_power_set not in mm_sapphire_power_setpoint_sets:
                raise PycroConnectionError("Micromanager is missing SapphirePowerSetpoint setting '{}'".format(s_power_set))
        
        
        
        
        
