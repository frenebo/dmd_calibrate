import paramiko
import json
import time

class RaspiController:
    def __init__(self, hostname, username, password):
        self.ssh_client =paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=hostname,username=username,password=password)
        

        self.remote_image_path = "dmd_show_image.jpg"
    
    def start_feh(self):
        stdin, stdout, stderr = self.ssh_client.exec_command("feh -Z" + self.remote_image_path + " &")
        script_output = stdout.readlines()
        script_err = stderr.readlines()
        
        if len(script_err)!= 0:
            text_stderr = "".join(script_err)
            text_stdout = "".join(script_output)
            raise Exception("Error with pi program:\nstderr:\n"+text_stderr+"\nstdout:\n" + text_stdout)

    def send_and_show_image_on_dmd(self, local_image_path):
        ftp_client=self.ssh_client.open_sftp()
        ftp_client.put(local_image_path, self.remote_image_path)
        ftp_client.close()
        print("Copied local image '{}' to Pi path '{}'".format(local_image_path, self.remote_image_path))

    def stop_showing_image_on_dmd(self):
        stdin, stdout, stderr = self.ssh_client.exec_command("pkill feh")
        
        script_output = stdout.readlines()
        script_err = stderr.readlines()
        
        if len(script_err)!= 0:
            text_stderr = "".join(script_err)
            text_stdout = "".join(script_output)
            raise Exception("Error with pi program:\nstderr:\n"+text_stderr+"\nstdout:\n" + text_stdout)
            
        