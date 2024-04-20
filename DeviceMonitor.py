import logging, re, time, json, os
from getpass import getpass
from netmiko import ConnectHandler
from datetime import datetime

class DeviceMonitor:

    def __init__(self, device, shutdown_event):
        self.device = device
        self.last_dot11_message = None
        self.dot11_message_count = 0
        self.ip = device['ip']
        self.shutdown_event = shutdown_event
        # Load configuration
        config = self.load_config()
        self.debug_list = config['debug_list']
        self.filter_list = config['filter_list']
        self.dot11_uplink_ev_regex = re.compile(config['dot11_uplink_ev_regex'])
        self.output_dir = config['outputdir']
        self.log_netmiko = config['log_netmiko']
        self.debug_netmiko = config['debug_netmiko']
        if self.debug_netmiko:
            self.setup_netmiko_debug_logging()
            self.device_logger = False
        elif self.log_netmiko:
            self.device_logger = False
        else:
            self.device_logger = self.setup_device_logger(device['ip'], config['outputdir'])

    @staticmethod
    def load_config():
        with open('config.json', 'r') as file:
            config = json.load(file)
        return config

    def setup_device_connection(self):
        # Setting up ConnectHandler with session_log
        if self.log_netmiko:
            """Set up device connection with session and optional debug logging."""
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs(self.output_dir, exist_ok=True)
            session_log_file = f"{self.output_dir}/netmiko_session_{self.device['ip']}_{timestamp}.log"
            net_connect = ConnectHandler(**self.device, session_log=session_log_file)
        else:
            net_connect = ConnectHandler(**self.device)
        return net_connect
    
    def setup_netmiko_debug_logging(self):
        """Setup debug logging for Netmiko-specific logs."""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{self.output_dir}/netmiko_debug_log_{timestamp}.log"
        
        # Set up Netmiko specific debug logging
        netmiko_logger = logging.getLogger("netmiko")
        netmiko_logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        netmiko_logger.addHandler(file_handler)
        netmiko_logger.propagate = False  # Stop the log messages from propagating to the root logger
        
        # If you want to also log to console
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # console_handler.setFormatter(formatter)
        # logging.getLogger().addHandler(console_handler)
        # netmiko_logger.addHandler(console_handler)

    def setup_device_logger(self, ip_address, output_dir='./output'):
        """Set up a logger for each device with a unique file including a timestamp."""
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a unique filename with date and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/device_monitor_debug_{ip_address}_{timestamp}.log"
        
        # Set up logging
        device_logger = logging.getLogger(f"device_{ip_address}")
        device_logger.setLevel(logging.DEBUG)
        device_logger.propagate = False
        
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        device_logger.addHandler(file_handler)
        
        return device_logger

    def log_to_console(self, message, level=logging.INFO):
                # Log to console conditionally
        if level == logging.INFO or level == logging.ERROR:
            logging.getLogger().info(message)

    def log_both_conditionally(self, message, level=logging.INFO, console=True):
        if self.device_logger:
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
        if console and (level == logging.INFO or level == logging.ERROR) :
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

            #with ConnectHandler(**self.device) as net_connect:
            with self.setup_device_connection() as net_connect:
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
                while not self.shutdown_event.is_set():
                    output = net_connect.read_channel()
                    self.process_output(output)
                    time.sleep(1)
                    # Manually flush the session log to ensure it's up-to-date
                    if hasattr(net_connect, 'session_log'):
                        net_connect.session_log.flush()
                # Send 'undebug all' command if the shutdown event is set
                if self.shutdown_event.is_set():
                    try:
                        self.log_netmiko = False
                        with self.setup_device_connection() as net_connect2:
                            net_connect2.send_command('u all')
                            self.log_both_conditionally(f"Undebug all sent to {ip}", logging.INFO)
                        while True:
                            remaining_output = net_connect.read_channel()
                            if not remaining_output:
                                break
                            self.process_output(remaining_output)
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
        match = self.dot11_uplink_ev_regex.search(line)
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