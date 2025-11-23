export interface NodeOverview {
  node_id: string;
  height: number;
  head_hash: string;
  last_block_time: number;
  total_accounts: number;
  total_balance: number;
}

export interface BlockSummary {
  height: number;
  block_hash: string;
  prev_hash: string;
  timestamp: number;
  proposer_id: string;
  tx_count: number;
}

export interface BlocksResponse {
  node_id: string;
  total: number;
  items: BlockSummary[];
}

export interface BlockDetail extends BlockSummary {
  tx_list: TransactionBody[];
}

export interface AccountEntry {
  address: string;
  balance: number;
}

export interface AccountsResponse {
  node_id: string;
  total: number;
  items: AccountEntry[];
}

export interface TransactionView {
  tx_id: string;
  sender: string;
  to: string;
  amount: number;
  nonce: number;
  block_height: number;
  block_hash: string;
}

export interface TransactionsResponse {
  node_id: string;
  items: TransactionView[];
}

export interface TransactionBody {
  tx_id?: string;
  sender: string;
  to: string;
  amount: number;
  nonce: number;
  signature?: string;
}
