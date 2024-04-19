from threading import Event
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from netmiko import ConnectHandler

import json, time, logging, signal

shutdown_event = Event()
shutdown_initiated = False


# Global logger setup for console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])


def handle_interrupt():
    global shutdown_initiated
    if not shutdown_initiated:
        logging.getLogger().info("Received keyboard interrupt, initiating shutdown.")
        shutdown_event.set()
        shutdown_initiated = True
        #raise KeyboardInterrupt  # Raise KeyboardInterrupt only here, centrally

def signal_handler(signal, frame):
    handle_interrupt()  # Use the same centralized handling logic

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

def log_to_both(logger, message, level=logging.INFO):
    """Log to both the specific device logger and the console."""
    if level == logging.DEBUG:
        logger.debug(message)
    elif level == logging.INFO:
        logger.info(message)
    elif level == logging.WARNING:
        logger.warning(message)
    elif level == logging.ERROR:
        logger.error(message)
    elif level == logging.CRITICAL:
        logger.critical(message)
    # Optionally log to global console at a different level or based on conditions
    logging.getLogger().info(message)  # This uses the root logger which has console handler


def connect_and_monitor(device):
    try:
        ip = device['ip']
        device_logger = setup_device_logger(ip)
        if 'password' not in device or device['password'] == "":
            device['password'] = getpass(f"Enter password for {device['ip']}: ")
        if 'secret' not in device or device['secret'] == "":
            device['secret'] = getpass(f"Enter enable password for {device['ip']}: ")

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
                            # Check the line against specific criteria
                            if "[DOT11_UPLINK_CONNECTED]" in line or \
                            "Aux roam switch radio role" in line or \
                            "[DOT11_UPLINK_FT_AUTHENTICATING]" in line or \
                            "target channel" in line or \
                            "DOT11-UPLINK_ESTABLISHED" in line or \
                            "Peer assoc event received from driver" in line:
                                # Set the flag to True since we have a relevant message
                                if not log_initial_message:
                                    log_to_both(device_logger, f"Messages from {device['ip']}")
                                    log_initial_message = True

                                # Handle the special case separately
                                if "Peer assoc event received from driver" in line:
                                    device_logger.debug(f"{line}\n")
                                    stats = net_connect.send_command('show wgb statistic roaming')
                                    log_to_both(device_logger, f"This is probably not so useful because it was not designed for dual radio:")
                                    log_to_both(device_logger, f"{stats}\n")
                                else:
                                    # Log the message normally for other criteria
                                    log_to_both(device_logger, f"{line}\n")
                            else:
                                # Log to debug without changing the initial log flag
                                device_logger.debug(f"{line}")
                time.sleep(1)
                log_initial_message = False

    except Exception as e:
        log_to_both(device_logger, f"An error occurred with {device['ip']}: {e}")
    finally:
        if 'net_connect' in locals():
            net_connect.send_command('u all')  # Cleanup command on shutdown

def main():
    with open('devices.json', 'r') as file:
        devices = json.load(file)
    
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [executor.submit(connect_and_monitor, device) for device in devices]
        
        # Use a loop to periodically check if all futures are done
        all_done = False
        while not all_done:
            all_done = True  # Assume all are done unless found otherwise
            for future in futures:
                try:
                    # Check if future is done; wait briefly
                    result = future.result(timeout=0.1)  # Adjust timeout as needed
                except TimeoutError:
                    all_done = False  # One or more futures are not done
                except Exception as e:
                    logging.getLogger().error(f"Error processing future: {str(e)}")
                    all_done = False  # Continue checking other futures

            if shutdown_event.is_set():
                logging.getLogger().info("Shutdown event is set. Breaking loop.")
                break

    # Shutdown message and cleanup
    logging.getLogger().info("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()