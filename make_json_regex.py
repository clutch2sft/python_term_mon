import json

def escape_string_for_json(original_string):
    # Use json.dumps to escape and format the string for JSON storage
    escaped_string = json.dumps(original_string)
    return escaped_string

# Example string
input_string = "IP: tableid=0, s=(\d+\.\d+\.\d+\.\d+) \(local\), d=(\d+\.\d+\.\d+\.\d+) \(Vlan\d+\), routed via FIB"


# Escape the string
escaped_json_string = escape_string_for_json(input_string)

print("Escaped JSON String:")
print(escaped_json_string)
