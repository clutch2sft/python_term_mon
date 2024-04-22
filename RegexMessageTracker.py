import re, json
import logging
from DeviceLogger import DeviceLogger
from ConfigurationLoader import ConfigLoader
class RegexMessageTracker:
    def __init__(self, ip_address, output_dir='./output'):
        """
        Initializes the RegexMessageTracker with a dictionary of regex patterns and sets up device-specific logging.
        Also sets up conditional console logging for specific alert strings.
        
        :param regex_patterns: Dictionary of regex patterns as named strings
        :param ip_address: IP address of the device to uniquely identify the log file
        :param output_dir: Directory to store log files
        :param alert_strings: List of strings that, when matched, should also log to the console
        """
        config_loader = ConfigLoader()
        config = config_loader.get_configuration()
        self.regex_patterns = config['regex_patterns']  # Assume regex patterns are provided in config
        self.alert_strings = config['alert_strings']  # Strings for console alerts
        self.ip = ip_address
        self.patterns = {key: re.compile(pattern) for key, pattern in self.regex_patterns.items()}
        self.last_matched = {}
        self.match_counts = {}
        self.first_matched_message = {}
        self.last_full_match = {}
        self.logger = DeviceLogger.get_logger(ip_address, output_dir, console_level=logging.WARNING)

    def process_line(self, line):
        """
        Process a line to check against stored regex patterns and specific alert strings.
        If the line matches a pattern and is different from the last match, update and log the previous with count.
        If no patterns match, log the line directly. If the line matches any alert string, log to console as well.
        
        :param line: The line of text to be processed
        """
        matched_any = False  # Flag to check if any pattern matches the current line
        for key, pattern in self.patterns.items():  # Iterate over all compiled regex patterns
            match = pattern.search(line)  # Search for the pattern in the current line
            if match:
                matched_any = True  # Set flag to True if a match is found
                # Get the full matched string
                matched_text = match.group(0)
                
                # Check if the current match is different from the last match stored for this regex key
                if self.last_matched.get(key) != matched_text:
                    # If there was a previous match (i.e., not None), log it along with its count
                    if self.last_matched.get(key) is not None:
                        # Log the previous message that initiated the current count and its count
                        self.log_message(key, self.first_matched_message[key], self.match_counts[key])
                    
                    # Update the last matched message to the current one and reset the count
                    self.last_matched[key] = matched_text
                    self.match_counts[key] = 1
                    self.first_matched_message[key] = line  # Store the current line as the first match for this pattern
                    # Log that a new match sequence has started - if desired uncomment if needed
                    #self.log_direct(f"New match for {key}: {line}, count reset")
                else:
                    # If the current match is the same as the last, increment the count
                    self.match_counts[key] += 1
                    # Update the last fully matched line to the current one for reference
                    self.last_full_match = line
                    # Log continuation is commented out to avoid excessive logs; uncomment if needed
                    #self.log_direct(f"Match for {key} continues: {matched_text}, count incremented to {self.match_counts[key]}")
            else:
                # If no pattern is matched, optionally log this information; commented out to avoid noise
                #self.log_direct(f"No match for {key} in line: {line}")
                pass
        # Check for alert string matches
        if any(alert in line for alert in self.alert_strings):
            self.log_to_console(line)
        elif not matched_any:
            # If the line did not match any pattern AND it wasn't set for alert, log it immediately
            self.log_direct(line)
            #pass

    def log_message(self, key, message, count):
        """
        Logs the message that has been tracked and has now changed using the device-specific logger.
        
        :param key: The name of the regex pattern that matched the message
        :param message: The message to log
        :param count: Number of times this message was seen before it changed
        """
        self.logger.info(f"From~{self.ip}:Pattern [{key}]: {message} (Count: {count})")

    def log_direct(self, line):
        """
        Logs the line directly when it matches no patterns using the device-specific logger.
        
        :param line: The line of text to log
        """
        self.logger.info(f"From~{self.ip}:{line}")

    def log_to_console(self, message):
        """
        Logs the message to the console specifically for alert strings.
        """
        self.logger.warning(f"From~{self.ip}:{message}")

    def finish(self):
        """
        Ensures all remaining messages are logged when monitoring is completed.
        """
        for pattern, message in self.first_matched_message.items():
            if message:
                self.log_message(pattern, message, self.match_counts[pattern])
