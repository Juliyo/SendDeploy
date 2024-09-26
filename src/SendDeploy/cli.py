# SendDeploy/cli.py

import argparse
import paramiko
from scp import SCPClient
import getpass
import json
import os

CONFIG_PATH = os.path.expanduser("~/.SendDeploy.json")
KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")  # Default SSH key path

def load_config():
    """Load configuration from the file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    """Save configuration to the file."""
    with open(CONFIG_PATH, 'w') as file:
        json.dump(config, file)

def create_ssh_client(server, user, password):
    """Create an SSH client and connect to the server."""
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=user, password=password)
    return ssh

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="A CLI tool to manage SSH keys and upload files via SCP")
    
    parser.add_argument("filename", help="The path to the file to upload (required if action is 'file')")

    args = parser.parse_args()

    # Load the last used configuration
    config = load_config()
    last_ip = config.get("ip", "")
    last_user = config.get("username", "")
    last_password = config.get("password", "")
    last_remote_path = config.get("remote_path", "")

    if not last_ip:
        print("No previous IP found. Please enter an IP address.")
        ssh_ip = input("Enter SSH server IP address: ")
        ssh_user = input("Enter SSH username: ")
        ssh_password = getpass.getpass("Enter SSH password: ")
        remote_path = input("Enter remote path to upload the file (e.g., /remote/path/): ")
    else:
        # Show the last used IP
        print(f"Last used IP: {last_ip}")
        ssh_ip = input("Enter SSH server IP address (leave blank to use last IP): ")
        # Use stored values if IP is left blank
        if not ssh_ip:
            if last_ip:
                ssh_ip = last_ip
                ssh_user = last_user
                ssh_password = last_password
                remote_path = last_remote_path
        else:
            # Ask user for other SSH details since a new IP was entered
            ssh_user = input("Enter SSH username: ")
            ssh_password = getpass.getpass("Enter SSH password: ")
            remote_path = input("Enter remote path to upload the file (e.g., /remote/path/): ")

    # Connect to the SSH server and upload the file
    try:
        ssh_client = create_ssh_client(ssh_ip, ssh_user, ssh_password)
        with SCPClient(ssh_client.get_transport()) as scp:
            scp.put(args.filename, remote_path)
            print(f"File '{args.filename}' successfully uploaded to {remote_path} on {ssh_ip}")

        # Save the SSH details to the config file
        config.update({"ip": ssh_ip, "username": ssh_user, "password": ssh_password, "remote_path": remote_path})
        save_config(config)

    except FileNotFoundError:
        print(f"Error: The file '{args.filename}' was not found.")
    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your SSH credentials.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'ssh_client' in locals():
            ssh_client.close()

if __name__ == "__main__":
    main()