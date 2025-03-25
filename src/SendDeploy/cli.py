import argparse
import paramiko
import json
import os
import curses
from scp import SCPClient
from tqdm import tqdm
import sys
import traceback

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'SendDeployV2.json')

# Function to load entries from the JSON file
def load_entries():
    """
    Loads connection entries from the SendDeployV2.json file.  Handles file not found and missing 'entries' key.

    Returns:
        dict: A dictionary containing the entries and last selected index.  Returns a default structure if the file doesn't exist.
    """
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
            if 'entries' not in data:
                data['entries'] = []
            if 'last_selected_idx' not in data:
                data['last_selected_idx'] = -1
            return data
    except FileNotFoundError:
        print(f"Warning: Configuration file not found at {CONFIG_PATH}. Creating a new one.")
        return {"entries": [], "last_selected_idx": -1}  # Return default structure if file does not exist
    except json.JSONDecodeError:
        print(f"Error: Configuration file at {CONFIG_PATH} is corrupted.  Overwriting with default settings.")
        return {"entries": [], "last_selected_idx": -1}

# Function to save entries to the JSON file, including the last selected index
def save_entries(entries, last_selected_idx):
    """
    Saves connection entries and the last selected index to the SendDeployV2.json file.

    Args:
        entries (list): The list of connection entries.
        last_selected_idx (int): The index of the last selected entry.
    """
    data = {"entries": entries, "last_selected_idx": last_selected_idx}
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving to configuration file: {e}")

# Function to clear all saved entries
def clear_entries():
    """
    Clears all saved connection entries from the SendDeployV2.json file.
    """
    # Clear the JSON file by saving an empty list and resetting the last selected index
    save_entries([], -1)
    print("All connections cleared.") # provide feedback

# Function to remove a specific entry by index
def remove_entry(entries, idx):
    """
    Removes a specific entry from the entries list by its index.

    Args:
        entries (list): The list of connection entries.
        idx (int): The index of the entry to remove.

    Returns:
        list: The modified list of entries, or the original list if the index was invalid.
    """
    if 0 <= idx < len(entries):
        del entries[idx]
        return entries  # Return modified list
    return entries

def create_ssh_client(server, user, password):
    """
    Creates an SSH client and connects to the server.  Handles connection errors.

    Args:
        server (str): The server address.
        user (str): The username.
        password (str): The password.

    Returns:
        paramiko.SSHClient: The SSH client object, or None on error.
    """
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(server, username=user, password=password, timeout=10) # added timeout
        return ssh
    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your SSH credentials.")
        return None
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while connecting to {server}: {e}")
        return None

# Function to create a progress bar and update it during the SCP transfer
def progress(filename, size, sent):
    """
    Updates the tqdm progress bar during the SCP transfer.

    Args:
        filename (str): The name of the file being transferred.
        size (int): The total size of the file.
        sent (int): The number of bytes sent so far.
    """
    # Update the progress bar with the sent data
    progress_bar.update(sent - progress_bar.n)

def send_file(filename, ssh_ip, ssh_user, ssh_password, remote_path):
    """
    Connects to an SSH server and uploads a file using SCP, with a progress bar.

    Args:
        filename (str): The path to the file to upload.
        ssh_ip (str): The IP address of the SSH server.
        ssh_user (str): The username for the SSH connection.
        ssh_password (str): The password for the SSH connection.
        remote_path (str): The destination path on the SSH server.
    """
    # Connect to the SSH server and upload the file
    ssh_client = create_ssh_client(ssh_ip, ssh_user, ssh_password)
    if ssh_client is None:
        return  # Exit if SSH connection failed

    try:
        # Create the SCP transport and SCPClient instance

        transport = ssh_client.get_transport()

        # Get the file size
        file_size = os.path.getsize(filename)

        # Create a progress bar for the upload
        global progress_bar # make it global so that it does not throw error if the function errors out.
        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=filename, ncols=100)

        with SCPClient(transport, progress=progress) as scp_client:
            # Upload the file with progress tracking
            scp_client.put(filename, remote_path)
            progress_bar.n = file_size
            progress_bar.refresh()
            progress_bar.close()
            tqdm.write(f"File '{filename}' successfully uploaded to {remote_path} on {ssh_ip}")


    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your SSH credentials.")
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc() # print the traceback
    finally:
        if 'ssh_client' in locals() and ssh_client: # check if ssh_client was assigned and is not None
            ssh_client.close()

# Function to display the interactive menu using curses
def interactive_select(stdscr, entries, last_selected_idx):
    """
    Displays an interactive menu in the terminal using curses, allowing the user to select a connection.

    Args:
        stdscr: The curses standard screen object.
        entries (list): A list of connection entries.
        last_selected_idx (int): The index of the last selected entry.

    Returns:
        int or None or str: The index of the selected entry, None to add a new entry,
                         'clear' to clear entries, 'remove',index to remove an entry or 'quit' to quit.
    """
    # Function to display the entries
    def display_menu(selected_idx):
        stdscr.clear()
        if not entries:
            stdscr.addstr(0, 0, "No connections found. Add a new connection", curses.A_BOLD)
        else:
            stdscr.addstr(0, 0, "Select a connection to copy file (Use arrow keys to navigate, Enter to select):", curses.A_BOLD)
        for idx, entry in enumerate(entries):
            if idx == selected_idx:
                stdscr.addstr(2 + idx, 2, f"> {entry['ssh_ip']} - {entry['ssh_user']} - {entry['remote_path']}", curses.A_REVERSE)
            else:
                stdscr.addstr(2 + idx, 2, f"  {entry['ssh_ip']} - {entry['ssh_user']} - {entry['remote_path']}")
        stdscr.addstr(len(entries) + 2, 0, "Press 'n' to add a new connection.", curses.A_BOLD)
        stdscr.addstr(len(entries) + 3, 0, "Press 'a' to clear all connections.", curses.A_BOLD)
        stdscr.addstr(len(entries) + 4, 0, "Press 'c' to remove the selected connection.", curses.A_BOLD)
        stdscr.addstr(len(entries) + 5, 0, "Press 'q' to quit.", curses.A_BOLD)
        stdscr.refresh()

    selected_idx = last_selected_idx  # Start with the last selected index
    display_menu(selected_idx)

    # Enable keypad mode to capture special keys
    stdscr.keypad(True)

    while True:
        try:
            key = stdscr.getch()

            if key == curses.KEY_UP:  # Up arrow key
                if selected_idx > 0:
                    selected_idx -= 1
            elif key == curses.KEY_DOWN:  # Down arrow key
                if selected_idx < len(entries) - 1:
                    selected_idx += 1
            elif key == 13:  # Enter key
                return selected_idx
            elif key == ord('n'):  # Press 'n' to add a new entry
                return None  # Indicate that we need to add a new entry
            elif key == ord('a'):  # Press 'a' to clear all entries
                return 'clear'  # Indicate that we need to clear all entries
            elif key == ord('c'):  # Press 'c' to remove the selected entry
                return 'remove', selected_idx  # Indicate that we need to remove the selected entry
            elif key == ord('q'):  # Press 'q' to exit program
                return 'quit'
            elif key == 3:  # ASCII for Ctrl+C
                raise KeyboardInterrupt

            display_menu(selected_idx)
        except Exception as e:
            curses.endwin()
            print(f"Error in interactive_select: {e}")
            traceback.print_exc()
            sys.exit(1)

# Function to add a new entry
def add_new_entry(stdscr):
    """
    Prompts the user to enter details for a new connection entry via the curses interface.

    Args:
        stdscr: The curses standard screen object.

    Returns:
        dict: A dictionary containing the new connection entry details,
              or None if the user cancels.
    """
    stdscr.clear()
    stdscr.addstr(0, 0, "Enter new ssh connection (Format: IP, User, Password, Remote Path):", curses.A_BOLD)
    stdscr.refresh()

    # Input for IP, user, and password
    stdscr.addstr(2, 0, "Enter SSH server IP address: ")
    curses.echo()
    ip = stdscr.getstr(3, 0, 30).decode('utf-8').strip()

    stdscr.addstr(5, 0, "Enter SSH username: ")
    user = stdscr.getstr(6, 0, 30).decode('utf-8').strip()

    stdscr.addstr(8, 0, "Enter SSH password: ")
    curses.noecho()
    password = stdscr.getstr(9, 0, 30).decode('utf-8').strip()

    stdscr.addstr(11, 0, "Enter remote path to upload the file (e.g., /remote/path/): ")
    curses.echo()
    remote_path = stdscr.getstr(12, 0, 30).decode('utf-8').strip()
    

    new_entry = {"ssh_ip": ip, "ssh_user": user, "ssh_password": password, "remote_path": remote_path}
    return new_entry

def application(stdscr):
    """
    Main application function to manage SSH connections and file uploads.

    Args:
        stdscr: The curses standard screen object.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="A CLI tool to manage SSH keys and upload files via SCP")

    parser.add_argument("--quiet", action="store_true", help="Allow executing the last executed connection")
    parser.add_argument("filename", help="The path to the file to upload (required if action is 'file')")

    args = parser.parse_args()

    curses.raw()  # Enable raw mode for precise signal handling
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()

    # Load existing entries and last selected index
    data = load_entries()
    entries = data["entries"]
    last_selected_idx = data["last_selected_idx"]

    if last_selected_idx == -1:
        last_selected_idx = 0

    if args.quiet:
        # Ends curses mode to display the selected entry details
        curses.endwin()
        if not entries:
            print("No connections found. Add a new connection.")
            return
        # After selecting an entry, show the selected entry details
        print(f"Copying file {args.filename} to: IP: {entries[last_selected_idx]['ssh_ip']}, User: {entries[last_selected_idx]['ssh_user']}, Remote path: {entries[last_selected_idx]['remote_path']}")
        send_file(args.filename, entries[last_selected_idx]['ssh_ip'], entries[last_selected_idx]['ssh_user'], entries[last_selected_idx]['ssh_password'], entries[last_selected_idx]['remote_path'])
        return

    while True:
        action = interactive_select(stdscr, entries, last_selected_idx)

        if action == 'quit':
            break  # Quit program

        if action == 'clear':  # User pressed 'a' to clear all entries
            clear_entries()
            entries = []
            last_selected_idx = -1 # reset last selected index
            stdscr.clear()
            stdscr.addstr(0, 0, "All connections have been cleared.")
            stdscr.refresh()
            stdscr.getch()  # Wait for user input before exiting
            save_entries(entries, last_selected_idx)
            continue

        if isinstance(action, tuple) and action[0] == 'remove':  # User pressed 'c' to remove the selected entry
            entries = remove_entry(entries, action[1])  # action[1] is the index to remove
            if not entries:
                last_selected_idx = -1 # reset
            else:
                last_selected_idx = min(last_selected_idx, len(entries) -1 ) # adjust last_selected_idx if necessary
            stdscr.clear()
            stdscr.addstr(0, 0, "Connection has been removed.")
            stdscr.refresh()
            stdscr.getch()  # Wait for user input before exiting
            save_entries(entries, last_selected_idx)
            continue

        if action is None:  # User pressed 'n' to add a new entry
            new_entry = add_new_entry(stdscr)
            if new_entry: # only add if new_entry is not None
                entries.append(new_entry)
                last_selected_idx = len(entries) - 1  # New entry is selected by default
                save_entries(entries, last_selected_idx)
            continue # Continue the loop to show the main menu

        else:
            last_selected_idx = action  # Update last selected index
            save_entries(entries, last_selected_idx)
            # Ends curses mode to display the selected entry details
            curses.endwin()

            # After selecting an entry, show the selected entry details
            print(f"Copying file {args.filename} to: IP: {entries[last_selected_idx]['ssh_ip']}, User: {entries[last_selected_idx]['ssh_user']}, Remote path: {entries[last_selected_idx]['remote_path']}")
            send_file(args.filename, entries[last_selected_idx]['ssh_ip'], entries[last_selected_idx]['ssh_user'], entries[last_selected_idx]['ssh_password'], entries[last_selected_idx]['remote_path'])
            return

        # Continue looping for the user to select another action or entry

    # Save the last selected index to the file so it can be remembered next time
    save_entries(entries, last_selected_idx)



def main():
    """
    Main entry point for the application.  Initializes curses and calls the application function.
    """
    try:
        stdscr = curses.initscr()
        application(stdscr)
    except KeyboardInterrupt:
        print("\nProgram exited by user (Ctrl+C).")
        curses.endwin()
        sys.exit(0)
    except Exception as e:
        curses.endwin()
        print(f"Unhandled exception: {e}")
        traceback.print_exc() # print the traceback
        sys.exit(1)
    finally:
        curses.endwin()
        

if __name__ == "__main__":
    main()
