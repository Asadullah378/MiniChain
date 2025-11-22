from storage.json_operations import read_json_file

def get_peer_addresses():

    addresses = read_json_file("seed_addresses.json")
    if addresses == None:
        print("Returning a dummy address list")
        return ["localhost:5001", "localhost:5002"]
    return addresses["peers"]
