import bisect

class SortedList:
    def __init__(self):
        self._list = []
        
    def add_item(self, item):
        bisect.insort(self._list, item)

    def remove_item(self, item):
        self._list.remove(item)
    