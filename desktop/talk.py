import paramiko
import sys

class RaspiController:
    def __init__(self, hostname, username, password, pi_interactive_script_path):
        self.ssh_client =paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=hostname,username=username,password=password)
        self.pi_interactive_script_path = pi_interactive_script_path


    def send_and_show_image_on_dmd(self, local_image_path):
        remote_image_path = "dmd_show_image.jpg"

        ftp_client=self.ssh_client.open_sftp()
        ftp_client.put(local_image_path, remote_image_path)
        ftp_client.close()
        print("Copied local image '{}' to Pi path '{}'".format(local_image_path, remote_image_path))

        instruction = {
            "command": "dmd_start_show_image",
            "loadpath" remote_image_path
        }

        result = self.execute_pi_instruction(instruction)
        if result["type"] == "success":
            print("Successfully ran command to show image '{}' on Pi".format(remote_image_path))
        else:
            raise Exception("Error from Pi when running command to show image on dmd: {}".format(str(result)))

    def stop_showing_image_on_dmd(self):
        result = self.execute_pi_instruction({
            "command": "dmd_kill_show_image"
        })
        if result["type"] == "success":
            print("Successfully ran command to kill dmd image show program on Pi")
        else:
            raise Exception("Error from Pi when running command to stop showing image on dmd: {}".format(str(result)))

    def take_picture_on_pi(self, local_image_path):
        if (not local_image_path.endswith(".tif")) and (not local_image_path.endswith(".tiff")):
            raise Exception("Pi camera will output a tif image, the filepath for copying the image should end with a .tif or .tiff. Invalid filepath '{}'".format(local_image_path))

        remote_image_path = "picam_image_capture.tif"

        result = self.execute_pi_instruction({
            "command": "takepicture",
            "savepath": remote_image_path,
        })
        if result["type"] == "success":
            print("Successfully ran command to capture image from Raspberry Pi Cam and save on Pi as '{}'".format(remote_image_path))
        else:
            raise Exception("Error from Pi when running command to capture image from camera and saving as '{}': {}".format(remote_image_path, str(result)))

        ftp_client = self.ssh_client.open_sftp()
        ftp_client.get(remote_image_path, local_image_path)
        ftp_client.close()

        print("Copied image '{}' from Pi to local file '{}'".format(remote_image_path, local_image_path))

    def execute_pi_instruction(self, instruction_object):
        instruction_string = json.dumps(instruction_object)
        # Start controller script on Pi and run command
        stdin, stdout, stderr = ssh.exec_command("python3 " + self.pi_interactive_script_path)
        stdin.write(instruction_string + "\n")
        script_output = stdout.readlines()
        command_result = json.loads(script_output[0])

        return command_result



if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Program for communicating with raspberry Pi over network (local network or internet)"
        "by running the matching interactive script on the Pi through ssh and sending and receiving files through ssh.")
    parser.add_argument('hostname', help="hostname to find raspberry pi, for example 'raspberrypi' is the default for a raspi on a local network")
    parser.add_argument('username', help="Username to login on raspberry pi")
    parser.add_argument('password', help="Password to login on raspberry pi")
    parser.add_argument('pi_interactive_script_path', help="Path for interactive python 3 script, the raspberry pi should have downloaded the matching interactive python script to run and receive instructions")

    args = parser.parse_args()

    controller = RaspiController(args.hostname, args.username, args.password, args.pi_interactive_script_path)