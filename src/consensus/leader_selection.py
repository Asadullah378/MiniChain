from consensus.data_structures import SortedList

class LeaderCircle:
    def __init__(self, client_id: str):
        self.current_leader = None
        self.client_id = client_id
        self.leader_turn_list = SortedList()

    def add_peer(self, peer_id: str):
        self.leader_turn_list.add_item(peer_id)
 
    def initialize_leader(self):
        self.current_leader = 0


