export const mockStatus = {
    node_id: "node-fallback-01",
    height: 42,
    peers_count: 3,
    mempool_size: 5,
    leader: "node-fallback-01",
    timestamp: Date.now() / 1000
};

export const mockBlocks = Array.from({ length: 5 }, (_, i) => ({
    height: 42 - i,
    hash: `0000abc123${42 - i}def456`,
    prev_hash: `0000abc123${41 - i}def456`,
    proposer_id: i % 2 === 0 ? "node-fallback-01" : "peer-node-02",
    timestamp: (Date.now() / 1000) - (i * 600), // 10 mins apart
    tx_count: Math.floor(Math.random() * 10) + 1
}));

export const mockMempool = [
    {
        id: "tx-pending-001",
        sender: "alice",
        recipient: "bob",
        amount: 10.5,
        timestamp: Date.now() / 1000
    },
    {
        id: "tx-pending-002",
        sender: "charlie",
        recipient: "dave",
        amount: 5.0,
        timestamp: (Date.now() / 1000) - 120
    },
    {
        id: "tx-pending-003",
        sender: "eve",
        recipient: "frank",
        amount: 100,
        timestamp: (Date.now() / 1000) - 300
    }
];
