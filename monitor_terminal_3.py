from threading import Event

shutdown_event = Event()

def connect_and_monitor(device):
    try:
        with ConnectHandler(**device) as net_connect:
            net_connect.enable()

            if shutdown_event.is_set():
                return
            
            output = net_connect.send_command('terminal monitor')
            log_to_both(f"Connected to {device['ip']} - {output}")

            if shutdown_event.is_set():
                return

            output = net_connect.send_command('debug wgb uplink event')
            log_to_both(f"Debug set on {device['ip']} - {output}")
    
    except Exception as e:
        log_to_both(f"An error occurred with {device['ip']}: {e}")

def main():
    try:
        with open('devices.json', 'r') as file:
            devices = json.load(file)
        
        executor = ThreadPoolExecutor(max_workers=len(devices))
        futures = [executor.submit(connect_and_monitor, device) for device in devices]

        try:
            for future in futures:
                future.result()
        except KeyboardInterrupt:
            log_to_both("Received keyboard interrupt, initiating shutdown.")
            shutdown_event.set()
            raise

    finally:
        executor.shutdown(wait=True)
        log_to_both("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    main()
