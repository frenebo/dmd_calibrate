import paramiko
import json
import time
import os

def save_local_img_for_dmd(np_float_img, path):
    assert np_float_img.dtype == float, "Image should be float array"
    assert np.all(np_float_img >= 0), "Image should have no negative brightness values"
    assert np.all(np_float_img <= 1), "Image should have no brightness values greater than 1"
    assert np_float_img.shape == (DMD_H, DMD_W), "Numpy float image should have shape {}, instead received  {}".format((DMD_H, DMD_W), np_float_img.shape)

    max_int16 =  np.iinfo(np.uint16).max

    np_int8_img = (np_float_img *  max_int16 ).astype(np.uint16)


    tifffile.imwrite(path, np_int8_img)

class RaspiConnectionError(Exception):
    pass


# class StandInRaspiImageSender:
#     def __init__(self):
#         pass
    
#     def 

class StandInRaspiImageSenderContextManager:
    def __init__(self):
        pass
    
    def __enter__(self):
        return StandInRaspiImageSender()
    
    def __exit__(self):
        pass

class StandInRaspiInterface:
    def __init__(self, hostname, username, password):
        pass
    
    def image_sender(self):
        return StandInRaspiImageSenderContextManager()

class RaspiImageSender:
    def __init__(self, ssh_client, local_image_temp_dirpath, raspi_remote_img_dirpath):
        self.ssh_client = ssh_client
        self.local_image_temp_dirpath = local_image_temp_dirpath
        self.sent_image_name_counter = 0
        self.tiffname_currently_on_pi = None
        self.raspi_remote_img_dirpath = raspi_remote_img_dirpath
        
        self.remote_image_folder = self.raspi_remote_img_dirpath + "/slideshow_image_files"
        self.remote_slideshow_symlinks_folder = self.raspi_remote_img_dirpath + "/slideshow_symlinks"
        
        self._feh_running = False
    
    def start_feh(self):
        # Make directory for slideshow symlinks to images, if it doesn't exist already
        stdin, stdout, stderr = self.ssh_client.exec_command("mkdir -p '{}'".format(self.remote_slideshow_symlinks_folder))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)

        # Make directory for image files themselves, if it doesn't exist already
        stdin, stdout, stderr = self.ssh_client.exec_command("mkdir -p '{}'".format(self.remote_image_folder))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)

        # Clear out symlink directory in case it has leftover files from before
        stdin, stdout, stderr = self.ssh_client.exec_command("rm '{}'/*".format(self.remote_slideshow_symlinks_folder))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)
        
        # Clear out image file directory in case it has leftover files from before
        stdin, stdout, stderr = self.ssh_client.exec_command("rm '{}'/*".format(self.remote_image_folder))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)
        
        # Make placeholder with ImageMagick's convert command
        # Put placeholder image in image folder and symlink in slideshow folder, so feh program doesn't exit 
        # because it has nothing to show in slideshow symlink folder
        placeholder_tiff_name = "placeholder.tiff"
        placeholder_tiff_path = self.remote_image_folder + "/" + placeholder_tiff_name
        placeholder_symlink_path = self.remote_slideshow_symlinks_folder + "/" + placeholder_tiff_name

        placeholder_command = "convert -size 100x100 xc:black '{}'".format(placeholder_tiff_path)
        print("Creating placeholder image: {}".format(placeholder_command))
        stdin, stdout, stderr = self.ssh_client.exec_command(placeholder_command)
        self._raise_exception_if_stderr_not_empty(stdout, stderr)

        stdin, stdout, stderr = self.ssh_client.exec_command("ln -fs '{}' '{}'".format(placeholder_tiff_path, placeholder_symlink_path))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)
        self.tiffname_currently_on_pi = placeholder_tiff_name

        # Execute command and detach
        # This starts a slideshow that doesn't switch slides by itself, but we can put a new file on raspberry pi,
        # create a symlink to it inside the slideshow folder, then remove the previous file from symlink directory and file directory,
        # and upon the reload that happens every n second (specified in the command), it'll switch to the other symlink to the new file.
        # Using symlinks because it's probably less risky as far as deleting a file while it's still being read. This seems
        # unlikely, but I'm doing it this way just in case
        
        feh_command = "export DISPLAY=:0; feh --reload 0.1 --hide-pointer --fullscreen --auto-zoom '{}' &".format(
            self.remote_slideshow_symlinks_folder,
        )
        stdin, stdout, stderr = self.ssh_client.exec_command(feh_command)
        
        self._feh_running = True
        print("Started feh: '{}'".format(feh_command))

    
    def _raise_exception_if_stderr_not_empty(self, stdout, stderr):
        script_output = stdout.readlines()
        script_err = stderr.readlines()
        
        if len(script_err)!= 0:
            text_stderr = "".join(script_err)
            text_stdout = "".join(script_output)
            raise Exception("Error with pi program:\nstderr:\n"+text_stderr+"\nstdout:\n" + text_stdout)
    
    
    def kill_feh(self):
        stdin, stdout, stderr = self.ssh_client.exec_command("pkill feh")
        
        self._raise_exception_if_stderr_not_empty(stdout, stderr)
        
        self._feh_running = False
        print("Killed feh")
    
    
    def send_image(self, np_float_img):
        if not self._feh_running:
            raise Exception("Can't send images to show without feh up and running, should call start_feh before send_image_to_feh")


        img_path = os.path.join(self.local_image_temp_dirpath, "imgfordmd.tiff")
        save_local_img_for_dmd(np_float_img, img_path)
        
        # Need a new name for the image
        while "pattern_{}.tiff".format(self.sent_image_name_counter) == self.tiffname_currently_on_pi:
            self.sent_image_name_counter += 1
        
        # This is the file name where we send the local image
        new_tiff_name = "pattern_{}.tiff".format(self.sent_image_name_counter)

        remote_path_for_image =   self.remote_image_folder + "/" + new_tiff_name
        remote_path_for_symlink = self.remote_slideshow_symlinks_folder + "/" + new_tiff_name
        
        # Send the image to the remote image folder
        ftp_client=self.ssh_client.open_sftp()
        ftp_client.put(local_image_path, remote_path_for_image)
        ftp_client.close()

        # Create a symlink in remote slideshow symlink folder so that feh will see it
        stdin, stdout, stderr = self.ssh_client.exec_command("ln -fs '{}' '{}'".format(
            remote_path_for_image,
            remote_path_for_symlink,
        ))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)
        
        print("Copied local image '{}' to Pi path '{}', with symlink to it at '{}'".format(local_image_path, remote_path_for_image, remote_path_for_symlink))

        # Remove symlink for old image, then on the next update feh should read from the new image
        old_symlinkpath = self.remote_slideshow_symlinks_folder + "/" + self.tiffname_currently_on_pi
        stdin, stdout, stderr = self.ssh_client.exec_command("rm '{}'".format(
            old_symlinkpath,
        ))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)

        time.sleep(0.2)

        old_imagepath = self.remote_image_folder + "/" + self.tiffname_currently_on_pi
        # Remove old file
        stdin, stdout, stderr = self.ssh_client.exec_command("rm '{}'".format(
            old_imagepath
        ))
        self._raise_exception_if_stderr_not_empty(stdout, stderr)

        print("Removed old '{}' and '{}' from Pi".format( old_symlinkpath, old_imagepath))

        # Set tiffname_currently_on_pi to the new filename
        self.tiffname_currently_on_pi = new_tiff_name


        # Come up with path for new image. Shouldn't be the same as the previous one

    
    

class RaspiImageSenderContextManager:
    def __init__(self, ssh_client, img_tempdirpath, raspi_remote_img_dirpath):
        self.ssh_client = ssh_client
        self.img_tempdirpath = img_tempdirpath
        self.raspi_remote_img_dirpath = raspi_remote_img_dirpath
        
        self.entered = False
        self.exited = False
    
    def __enter__(self):
        if self.entered:
            raise RuntimeError("__enter__ has been called twice on RaspiImageSenderContextManager - only meant to be used once!")
        self.entered = True
        
        self.sender = RaspiImageSender(self.ssh_client, self.img_tempdirpath, self.raspi_remote_img_dirpath)
        self.sender.start_feh()
    
    def __exit__(self):
        if not self.entered:
            raise RuntimeError("__exit__ called on RaspiImageSenderContextManager without __enter__ called.")
        self.sender.kill_feh()
        self.exited = True


class RaspiInterface:
    def __init__(self, hostname, username, password, tempdirpath):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.ssh_client.connect(hostname=hostname, username=username, password=password)
        except Exception as e:
            raise RaspiConnectionError("SSH connection: {}".format(str(e)))
            
        
        self.tiffname_currently_on_pi = None
        self.raspi_remote_img_dirpath = "/home/pi/Pictures/display_images_workdirectory"
        # self.remote_image_folder = "/home/pi/Pictures/pics_to_show_files"
        # self.remote_slideshow_symlinks_folder = "/home/pi/Pictures/slideshow_symlinks"
        self.sent_image_name_counter = 1
        
        self.last_created_raspi_image_context_manager = None
        
        self.tempdirpath = tempdirpath
        os.makedirs(self.tempdirpath, exist_ok=True)
        
        self.image_sender_tempdirpath = os.path.join(self.tempdirpath, "raspiImageSenderTmpImages")
        os.makedirs(self.image_sender_tempdirpath, exist_ok=True)
        
    
    def image_sender(self):
        if self.last_created_raspi_image_context_manager is not None:
            if (last_created_raspi_image_context_manager.entered and
                not last_created_raspi_image_context_manager.exited):
                raise RuntimeError(
                    "Cannot create new image sender until previous one has " +
                    "finished running - Raspi can only have one running at a given time.")
        
        # @TODO find out how __enter__ __exit__ logic is really supposed to work and implement better
        context_manager = RaspiImageSenderContextManager(self.ssh_client, self.image_sender_tempdirpath, self.raspi_remote_img_dirpath)
        self.last_created_raspi_image_context_manager = context_manager
        return context_manager
        