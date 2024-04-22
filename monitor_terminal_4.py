from threading import Event
from concurrent.futures import ThreadPoolExecutor
from DeviceMonitor import DeviceMonitor
import json, time, logging, signal
from ConfigurationLoader import ConfigLoader
from DeviceLogger import DeviceLogger

shutdown_event = Event()
shutdown_initiated = False

def handle_interrupt(logger):
    global shutdown_initiated
    if not shutdown_initiated:
        logger.warning("Received keyboard interrupt, initiating shutdown.")
        shutdown_event.set()
        shutdown_initiated = True

def signal_handler(logger):
    def handle_signal(signum, frame):
        handle_interrupt(logger)
    return handle_signal

def main(wkst_logger):
    wkst_logger.warning("Entering device monitor loop.")
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [executor.submit(DeviceMonitor(device, shutdown_event).connect_and_monitor) for device in devices]
        
        while not all(future.done() for future in futures):
            time.sleep(0.1)  # Adjust as necessary to reduce busy waiting
        
        if shutdown_event.is_set():
            wkst_logger.warning("Shutdown event is set. Breaking loop.")

    wkst_logger.warning("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    config_loader = ConfigLoader()
    devices = config_loader.get_devices()
    config = config_loader.get_configuration()
    wkst_logger = DeviceLogger.get_logger("workstation", config['output_dir'], config.get('console_level', None), format = config['log_format'])
    signal.signal(signal.SIGINT, signal_handler(wkst_logger))
    main(wkst_logger)
