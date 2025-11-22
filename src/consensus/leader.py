# add mem_pool as dep injection
# class carries out leader's duties
class Leader:
    def __init__(self, mem_pool):
        self.mem_pool = mem_pool
