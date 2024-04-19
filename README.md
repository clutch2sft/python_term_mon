# python_term_mon
monitor python sessions

You need to install netmiko for yourself.

"pip install netmiko"

No other dependancies.

Copy devices.json.sample to devices.json and update information in devices.json to match the devices you want to monitor.

To run:

python ./monitor_temrinal_3.py

This will create log file in your current working directory for each device in devices.json.

Also note this from devices.json.sample

        "__comments__": [
            "Copy this file to devices.json and update it with your device information",
            "ip is the device ip address",
            "username is the username to use to login to the device",
            "password is the ssh users loging password if not provided here we call getpass() later",
            "secret is the enable password of the device and if not provided we call getpass() later",
            "leaving passwords empty is preferred for production use as getpass() is more secure",
            "it is the authors opinion that putting password here as shown for device 2 below for lab use is ok"
          ]

Your devices.json file is excluded from github through .gitignore for your own safety.


