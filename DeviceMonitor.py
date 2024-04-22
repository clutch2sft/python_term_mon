import logging, time
from getpass import getpass
from netmiko import ConnectHandler
from datetime import datetime
from RegexMessageTracker import RegexMessageTracker  # Assume the tracker class is imported
from DeviceLogger import DeviceLogger
from ConfigurationLoader import ConfigLoader
class DeviceMonitor:

    def __init__(self, device, shutdown_event):
        self.device = device
        self.ip = device['ip']
        self.shutdown_event = shutdown_event
        config_loader = ConfigLoader()
        config = config_loader.get_configuration()
        self.debug_list = config['debug_list']
        self.output_dir = config['output_dir']
        self.log_netmiko = config['log_netmiko']
        self.debug_netmiko = config['debug_netmiko']
        self.console_level = config.get('console_level', None)
        self.log_format = config['log_format']
        # Convert console_level string to actual logging level
        console_level = getattr(logging, self.console_level) if self.console_level else None
        # Initialize RegexMessageTracker only if logging via Netmiko is not set
        if not self.log_netmiko and not self.debug_netmiko:
            self.device_logger = DeviceLogger.get_logger(self.ip, self.output_dir, console_level=self.console_level, format = self.log_format)
            self.tracker = RegexMessageTracker(self.ip, self.output_dir)
        elif self.debug_netmiko:
            self.setup_netmiko_debug_logging()
            self.device_logger = None
        else:
            self.device_logger = None

    def setup_device_connection(self):
        if self.log_netmiko:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_log_file = f"{self.output_dir}/netmiko_session_{self.ip}_{timestamp}.log"
            return ConnectHandler(**self.device, session_log=session_log_file)
        return ConnectHandler(**self.device)

    def setup_netmiko_debug_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{self.output_dir}/netmiko_debug_log_{timestamp}.log"
        netmiko_logger = logging.getLogger("netmiko")
        netmiko_logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        netmiko_logger.addHandler(file_handler)
        netmiko_logger.propagate = False

    def process_output(self, output):
        if output and self.tracker:
            lines = output.split('\n')
            for line in lines:
                if line.strip():
                    self.tracker.process_line(line)

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
                output = net_connect.send_command('u all')
                self.device_logger.warning(f"Connected to {ip} - Set undebug all as safety:{output}")
                output = net_connect.send_command('terminal monitor')
                self.device_logger.warning(f"{ip}:Terminal Monitor Set:{output}")
                #Check if there are any debug commands to execute
                if self.debug_list:
                    for command in self.debug_list:
                        output = net_connect.send_command(command)
                        self.device_logger.warning(f"Debug set on {ip} - Command: {command}, Output: {output}")
                else:
                    self.device_logger.warning(f"No debug commands configured for {ip}")
                # output = net_connect.send_command('debug wgb uplink event')
                # logging.info(f"Debug set on {ip} - {output}")
                while not self.shutdown_event.is_set():
                    output = net_connect.read_channel()
                    self.process_output(output)
                    time.sleep(1)
                    # Manually flush the session log to ensure it's up-to-date
                    if hasattr(net_connect, 'session_log') and self.log_netmiko:
                        net_connect.session_log.flush()
                # Send 'undebug all' command if the shutdown event is set
                if self.shutdown_event.is_set():
                    try:
                        self.log_netmiko = False
                        with self.setup_device_connection() as net_connect2:
                            net_connect2.send_command('u all')
                            self.device_logger.warning(f"Undebug all sent to {ip}")
                        while True:
                            remaining_output = net_connect.read_channel()
                            if not remaining_output:
                                break
                            self.process_output(remaining_output)
                    except Exception as e:
                        self.device_logger.warning(f"Error sending undebug all to {ip}: {e}")

        except Exception as e:
            self.device_logger.warning(f"Error with device {ip}: {e}")
        finally:
            if self.tracker:
                self.tracker.finish()

