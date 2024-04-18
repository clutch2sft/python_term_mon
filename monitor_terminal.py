import json
import time
from getpass import getpass
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor

# Function to handle connection and commands for a single device
def connect_and_monitor(device):
    try:
        # Use getpass to securely input passwords if not set in the file
        if 'password' not in device or device['password'] == "":
            device['password'] = getpass(f"Enter password for {device['ip']}: ")
        if 'secret' not in device or device['secret'] == "":
            device['secret'] = getpass(f"Enter enable password for {device['ip']}: ")
        
        with ConnectHandler(**device) as net_connect:
            net_connect.enable()
            output = net_connect.send_command('terminal monitor')
            print(f"Connected to {device['ip']} - {output}")
            output = net_connect.send_command('debug wgb uplink event')
            print(f"Debug set on {device['ip']} - {output}")
            # Example loop to continuously read output
            #for _ in range(10):  # Replace with while True for indefinite monitoring
            # Changed to a while loop for continuous monitoring
            try:
                while True:
                    output = net_connect.read_channel()
                    if output:
                        if "DOT11_UPLINK_EV: parent_rssi:" not in output:
                            print(f"Output from {device['ip']}:\n{output}")
                    time.sleep(1)
            except KeyboardInterrupt:
                # Cleanup code to run when there's a keyboard interrupt
                print("\nInterrupt received, sending cleanup command...")
                cleanup_output = net_connect.send_command('u all')
                print(f"Cleanup command output from {device['ip']}:\n{cleanup_output}")
                print("Exiting gracefully.")
                exit

    except Exception as e:
        print(f"An error occurred with {device['ip']}: {e}")

# Load device configurations from a JSON file
with open('devices.json', 'r') as file:
    devices = json.load(file)

# Using ThreadPoolExecutor to handle multiple devices concurrently
with ThreadPoolExecutor(max_workers=len(devices)) as executor:
    executor.map(connect_and_monitor, devices)
