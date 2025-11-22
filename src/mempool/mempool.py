"""Transaction mempool for pending transactions."""

from typing import Dict, List, Optional, Set
from src.chain.block import Transaction


class Mempool:
    """Manages pending transactions before they're included in blocks."""
    
    def __init__(self):
        """Initialize empty mempool."""
        self.transactions: Dict[str, Transaction] = {}  # tx_id -> Transaction
        self.seen_tx_ids: Set[str] = set()
    
    def add_transaction(self, tx: Transaction) -> bool:
        """
        Add a transaction to the mempool.
        
        Args:
            tx: Transaction to add
        
        Returns:
            True if added, False if already exists
        """
        if tx.tx_id in self.transactions:
            return False
        
        self.transactions[tx.tx_id] = tx
        self.seen_tx_ids.add(tx.tx_id)
        return True
    
    def remove_transaction(self, tx_id: str) -> bool:
        """
        Remove a transaction from the mempool.
        
        Args:
            tx_id: ID of transaction to remove
        
        Returns:
            True if removed, False if not found
        """
        if tx_id in self.transactions:
            del self.transactions[tx_id]
            return True
        return False
    
    def remove_transactions(self, tx_ids: List[str]):
        """Remove multiple transactions from mempool."""
        for tx_id in tx_ids:
            self.remove_transaction(tx_id)
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        return self.transactions.get(tx_id)
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions in mempool."""
        return list(self.transactions.values())
    
    def get_transactions(self, count: int) -> List[Transaction]:
        """
        Get up to N transactions from mempool.
        
        Args:
            count: Maximum number of transactions to return
        
        Returns:
            List of transactions
        """
        return list(self.transactions.values())[:count]
    
    def has_transaction(self, tx_id: str) -> bool:
        """Check if transaction exists in mempool."""
        return tx_id in self.transactions
    
    def has_seen(self, tx_id: str) -> bool:
        """Check if we've seen this transaction ID (even if removed)."""
        return tx_id in self.seen_tx_ids
    
    def size(self) -> int:
        """Get number of transactions in mempool."""
        return len(self.transactions)
    
    def clear(self):
        """Clear all transactions from mempool."""
        self.transactions.clear()
    
    def get_tx_ids(self) -> Set[str]:
        """Get set of all transaction IDs in mempool."""
        return set(self.transactions.keys())

