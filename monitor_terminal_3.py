from threading import Event
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from netmiko import ConnectHandler
import json, time, logging, signal, re

# Regular expression to match and capture parts of the DOT11_UPLINK_EV message
dot11_uplink_ev_regex = re.compile(r"DOT11_UPLINK_EV: parent_rssi: (-\d+), configured low rssi: (-\d+) serving (\d+) scanning (\d+)")

class DeviceMonitor:

    # Define class-level attribute for debug commands
    debug_list = [
        'debug wgb uplink event',
        'debug wgb uplink scan info',  # Add additional default debug commands as needed
    ]

    # Define a class-level attribute for the filter list
    filter_list = [
        "[DOT11_UPLINK_CONNECTED]",
        "Aux roam switch radio role",
        "[DOT11_UPLINK_FT_AUTHENTICATING]",
        "target channel",
        "DOT11-UPLINK_ESTABLISHED",
        "Peer assoc event received from driver"
    ]

    def __init__(self, device):
        self.device = device
        self.last_dot11_message = None
        self.dot11_message_count = 0
        self.device_logger = self.setup_device_logger(device['ip'])
        self.ip = device['ip']

    def setup_device_logger(self, ip_address):
        """Set up a logger for each device with a unique file."""
        device_logger = logging.getLogger(f"device_{ip_address}")
        device_logger.setLevel(logging.DEBUG)
        device_logger.propagate = False
        file_handler = logging.FileHandler(f'debug_{ip_address}.log')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        device_logger.addHandler(file_handler)
        return device_logger

    def log_both_conditionally(self, message, level=logging.INFO, console=True):
        """Log to both the specific device logger and optionally to the console."""
        if level == logging.DEBUG:
            self.device_logger.debug(message)
        elif level == logging.INFO:
            self.device_logger.info(message)
        elif level == logging.WARNING:
            self.device_logger.warning(message)
        elif level == logging.ERROR:
            self.device_logger.error(message)
        elif level == logging.CRITICAL:
            self.device_logger.critical(message)
        
        # Log to console conditionally
        if console and level == logging.INFO:
            logging.getLogger().info(message)

    def log_dot11_message(self):
        """Log the repeated message count only to the file."""
        if self.last_dot11_message and self.dot11_message_count > 0:
            # Log only to the device logger by setting console=False
            self.log_both_conditionally(f"{self.ip}:{self.last_dot11_message} has repeated {self.dot11_message_count} times", logging.INFO, console=False)
            self.dot11_message_count = 0

    def connect_and_monitor(self):
        ip = self.device['ip']
        try:
            if 'password' not in self.device or self.device['password'] == "":
                self.device['password'] = getpass(f"Enter password for {ip}: ")
            if 'secret' not in self.device or self.device['secret'] == "":
                self.device['secret'] = getpass(f"Enter enable password for {ip}: ")

            with ConnectHandler(**self.device) as net_connect:
                net_connect.enable()
                output = net_connect.send_command('terminal monitor')
                logging.info(f"Connected to {ip} - {output}")
                #Check if there are any debug commands to execute
                if self.debug_list:
                    for command in self.debug_list:
                        output = net_connect.send_command(command)
                        self.log_both_conditionally(f"Debug set on {ip} - Command: {command}, Output: {output}", logging.INFO)
                else:
                    self.log_both_conditionally(f"No debug commands configured for {ip}", logging.INFO)
                # output = net_connect.send_command('debug wgb uplink event')
                # logging.info(f"Debug set on {ip} - {output}")
                while not shutdown_event.is_set():
                    output = net_connect.read_channel()
                    self.process_output(output)
                    time.sleep(1)   
                # Send 'undebug all' command if the shutdown event is set
                if shutdown_event.is_set():
                    try:
                        net_connect.send_command('undebug all')
                        self.log_both_conditionally(f"Undebug all sent to {ip}", logging.INFO)
                    except Exception as e:
                        self.log_both_conditionally(f"Error sending undebug all to {ip}: {e}", logging.ERROR)

        except Exception as e:
            logging.getLogger().error(f"Error with device {ip}: {e}")
        finally:

            self.log_dot11_message()

    def process_output(self, output):
        if output:
            lines = output.split('\n')
            for line in lines:
                if line.strip():
                    self.process_line(line)

    def process_line(self, line):
        match = dot11_uplink_ev_regex.search(line)
        if match:
            current_message = match.group(0)
            if current_message != self.last_dot11_message:
                self.log_dot11_message()
                self.last_dot11_message = current_message
            self.dot11_message_count += 1
        else:
            # Check if the line should be logged at INFO level based on the filter list
            log_level = logging.INFO if any(filter_item in line for filter_item in self.filter_list) else logging.DEBUG
            self.log_both_conditionally(f"{self.device['ip']}:{line}", log_level)

shutdown_event = Event()
shutdown_initiated = False

def handle_interrupt():
    global shutdown_initiated
    if not shutdown_initiated:
        logging.getLogger().info("Received keyboard interrupt, initiating shutdown.")
        shutdown_event.set()
        shutdown_initiated = True

def signal_handler(signal, frame):
    handle_interrupt()

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    with open('devices.json', 'r') as file:
        devices = json.load(file)
    
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [executor.submit(DeviceMonitor(device).connect_and_monitor) for device in devices]
        
        while not all(future.done() for future in futures):
            time.sleep(0.1)  # Adjust as necessary to reduce busy waiting
        
        if shutdown_event.is_set():
            logging.getLogger().info("Shutdown event is set. Breaking loop.")

    logging.getLogger().info("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
