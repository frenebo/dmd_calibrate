import paramiko
import json

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
            "loadpath": remote_image_path,
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

    def execute_pi_instruction(self, instruction_object):
        instruction_string = json.dumps(instruction_object)
        # Start controller script on Pi and run command
        stdin, stdout, stderr = self.ssh_client.exec_command("python3 " + self.pi_interactive_script_path)
        stdin.write(instruction_string + "\n")
        script_output = stdout.readlines()
        command_result = json.loads(script_output[0])

        return command_result


