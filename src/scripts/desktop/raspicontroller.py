import paramiko
import json
import time

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
        poll_wait_time = 0.1
        instruction_string = json.dumps(instruction_object)
        # Start controller script on Pi and run command
        stdin, stdout, stderr = self.ssh_client.exec_command("python3 " + self.pi_interactive_script_path)
        print("Sending instructions:\n{}".format(instruction_string))
        stdin.write(instruction_string + "\n")

        output_received = False
        while True:
            script_output = stdout.readlines()
            script_err = stderr.readlines()

            if len(script_err)!= 0:
                text_stderr = "".join(script_err)
                text_stdout = "".join(script_output)
                raise Exception("Error with pi program:\nstderr:\n"+text_stderr+"\nstdout:\n" + text_stdout)

            if len(script_output) > 1:
                raise Exception("Pi script output more than one line, instead of a clear single response: "+str(script_output))
            elif len(script_output) == 1:
                command_result = json.loads(script_output[0])
                break
            else:
                time.sleep(poll_wait_time)

            # time.sleep(poll_wait_time)

        # script_output = stdout.readlines()
        # command_result = json.loads(script_output[0])

        return command_result


