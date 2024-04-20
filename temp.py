import logging

# Global logger setup for console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

def setup_device_logger(ip_address):
    """Set up a logger for each device with a unique file."""
    device_logger = logging.getLogger(f"device_{ip_address}")
    device_logger.setLevel(logging.DEBUG)  # Capture all logs for the device
    device_logger.propagate = False  # Stop logs from propagating to the root logger

    # File handler for device-specific logs
    file_handler = logging.FileHandler(f'debug_{ip_address}.log')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    device_logger.addHandler(file_handler)
    return device_logger

# Usage within a function
def connect_and_monitor(device):
    ip = device['ip']
    device_logger = setup_device_logger(ip)
    device_logger.debug("Device-specific debug message")  # Only to device's log file
    device_logger.info("Device-specific info message")    # Only to device's log file
    logging.info("General info message")                  # To console (and any configured global file handlers)

# Example device setup
device_info = {'ip': '192.168.1.100'}
connect_and_monitor(device_info)



def connect_and_monitor(device):
    try:
        ip = device['ip']
        device_logger = setup_device_logger(ip)
        if 'password' not in device or device['password'] == "":
            device['password'] = getpass(f"Enter password for {device['ip']}: ")
        if 'secret' not in device or device['secret'] == "":
            device['secret'] = getpass(f"Enter enable password for {device['ip']}: ")
        global last_dot11_message
        global dot11_message_count
        with ConnectHandler(**device) as net_connect:
            net_connect.enable()
            output = net_connect.send_command('terminal monitor')
            logging.info(f"Connected to {device['ip']} - {output}")
            output = net_connect.send_command('debug wgb uplink event')
            logging.info(f"Debug set on {device['ip']} - {output}")

            # Monitoring loop
            while not shutdown_event.is_set():
                output = net_connect.read_channel()
                if output:
                    lines = output.split('\n')
                    # Initialize a flag to check if any relevant message has been logged
                    log_initial_message = False

                    for line in lines:
                        if line.strip():
                            # Extract the specific message type with numbers
                            match = dot11_uplink_ev_regex.search(line)
                            if match:
                                current_message = match.group(0)  # Capture the full matching string, including numbers
                                if current_message != last_dot11_message:
                                    # If the current message is different from the last, log the last message count
                                    log_dot11_message()
                                    last_dot11_message = current_message  # Update the last message
                                # Increment count for the current message
                                dot11_message_count += 1
                            else:
                                # Process other types of messages with existing logic
                                if "[DOT11_UPLINK_CONNECTED]" in line or \
                                "Aux roam switch radio role" in line or \
                                "[DOT11_UPLINK_FT_AUTHENTICATING]" in line or \
                                "target channel" in line or \
                                "DOT11-UPLINK_ESTABLISHED" in line or \
                                "Peer assoc event received from driver" in line:
                                    if not log_initial_message:
                                        log_to_both(device_logger, f"Messages from {device['ip']}")
                                        log_initial_message = True

                                    if "Peer assoc event received from driver" in line:
                                        device_logger.debug(f"{line}\n")
                                        stats = net_connect.send_command('show wgb statistic roaming')
                                        log_to_both(device_logger, "This is probably not so useful because it was not designed for dual radio:")
                                        log_to_both(device_logger, f"{stats}\n")
                                    else:
                                        log_to_both(device_logger, f"{line}\n")
                                else:
                                    device_logger.debug(f"{line}")
                log_dot11_message()
                time.sleep(1)
                log_initial_message = False

    except Exception as e:
        log_to_both(device_logger, f"An error occurred with {device['ip']}: {e}")
    finally:
        if 'net_connect' in locals():
            net_connect.send_command('u all')  # Cleanup command on shutdown
