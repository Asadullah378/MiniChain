from consensus.data_structures import LeaderCandidateList


class NextLeaderPool:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self._leader_candidate_list = LeaderCandidateList()

    def reset_next_leader_candidate(self):
        self._leader_candidate_list.reset(self.client_id)

    def add_peer(self, peer_id: str):
        self._leader_candidate_list.add_item(peer_id)

    def remove_peer(self, peer_id: str):
        self._leader_candidate_list.remove_item(peer_id)

    def next_leader_candidate(self):
        return self._leader_candidate_list.next_candidate()
