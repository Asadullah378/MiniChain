import json

def read_json_file(filename):
    try:
        with open(filename, 'r') as file:
            data_dictionary = json.load(file)
            return data_dictionary
    
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found.")

        return None
    except json.JSONDecodeError:
        print(f"Error: The file {filename} contains invalid JSON.")
        return None