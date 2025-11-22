

def get_id_and_address_dict(address: str) -> dict:
    id = hash(address)
    id_adress_dict = {
        "id": id,
        "address": address
    }
    return id_adress_dict

if __name__ == "__main__":
    get_id_and_address_dict("localhost:5000")
    get_id_and_address_dict("127.0.0.1:5000")