import bisect

class LeaderCandidateList:
    def __init__(self):
        self._list = []
        self._leader_candidate = None

    def add_item(self, item: str) -> str:
        bisect.insort(self._list, item)

    def remove_item(self, item: str) -> None:
        self._list.remove(item)

    def next_candidate(self) -> str:
        index = self._leader_candidate + 1
        if index >= len(self._list) - 1:
            index = 0
        return self._list[index]

    def reset(self, item: str) -> None:
        self._leader_candidate = self._list.index(item)