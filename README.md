# python_term_mon


As of 4/22/2024 monitor_terminal_4 is pretty stable but not tested on multiple devices.  

To use monitor_terminal_4:

-make sure you install netmiko (pip install netmiko)
-copy config.json.sample to config.json and update config items as needed
- run: python monitor_terminal_4.py
- to end press {crtl c}


monitor_terminal_3 is the current stable version for use.  It will not recieve any more udpates.

monitor_terminal_4 is somewhat tested and adds a few things functionally:
-moves class DeviceMonitor out of the main file into a class file
-moves deduplication of messages based on regex into RegexMessageTracker class file
-creates a thread safe singleton like based logger with only 1 instanace for each ip address
-creates a singleton config loader class with only on instance for the entire running processes
-moves devices and configurable items into config.json
-sets output directory for log files and is configurable in config.json
-adds date/timestamp to debug log filenames
-info logs to file and warning logs to console and file
-handles case where user leaves __commments__ from config.json.sample in config.json


monitor python sessions - these scripts login to a cisco device and print the cisco device terminal output on the local terminal window of the machine they are run from.

Some of these scripts enable specific debugs to aid in troubleshooting/monitoring.

In short:

login to each deivce in devices.json
issue terminal monitor command
read the output 
print to local terminal

-or- 

login to each deivce in devices.json
issue terminal monitor command
issue any debug commands
read the output 
print to local terminal
issue undebug all on shutdown.

You need to install netmiko for yourself.

"pip install netmiko"

No other dependancies.

Copy devices.json.sample to devices.json and update information in devices.json to match the devices you want to monitor.

monitor_terminal_3.py has a list that looks like this:

    # Define class-level attribute for debug commands
    debug_list = [
        'debug wgb uplink event',
        'debug wgb uplink scan info',  # Add additional default debug commands as needed
    ]

Every debug command in this list will be executed afer a connection is made and terminal monitor mode is set.


monitor_terminal_3.py has a filter it looks like this:

    # Define a class-level attribute for the filter list
    filter_list = [
        "[DOT11_UPLINK_CONNECTED]",
        "Aux roam switch radio role",
        "[DOT11_UPLINK_FT_AUTHENTICATING]",
        "target channel",
        "DOT11-UPLINK_ESTABLISHED",
        "Peer assoc event received from driver"
    ]

Anything in the filter list prints to the local console and the local log file.  If nothing in the list matches then it only prints to the log file.

This helps you look for specfic messages on the console while reducing the clutter of messages you are less intersted in.

While at the same time everything is in the local log file for later analysis.

The initial list are things related to a roaming event on an IW9165 or (WGB).


To run:

python ./monitor_temrinal_3.py

This will create log file in your current working directory for each device in devices.json.

Also note this from devices.json.sample:

        "__comments__": [
            "Copy this file to devices.json and update it with your device information",
            "ip is the device ip address",
            "username is the username to use to login to the device",
            "password is the ssh users loging password if not provided here we call getpass() later",
            "secret is the enable password of the device and if not provided we call getpass() later",
            "leaving passwords empty is preferred for production use as getpass() is more secure",
            "it is the authors opinion that putting password here as shown for device 2 below for lab use is ok"
          ]

YOU SHOULD REMOVE THIS COMMENT IN YOUR ACTUAL devices.json file.  I didn't code to deal with it.  (Lazy).

Your devices.json file is excluded from github through .gitignore for your own safety.


