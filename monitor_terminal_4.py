from threading import Event
from concurrent.futures import ThreadPoolExecutor
from DeviceMonitor import DeviceMonitor
import json, time, logging, signal

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
        futures = [executor.submit(DeviceMonitor(device, shutdown_event).connect_and_monitor) for device in devices]
        
        while not all(future.done() for future in futures):
            time.sleep(0.1)  # Adjust as necessary to reduce busy waiting
        
        if shutdown_event.is_set():
            logging.getLogger().info("Shutdown event is set. Breaking loop.")

    logging.getLogger().info("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
