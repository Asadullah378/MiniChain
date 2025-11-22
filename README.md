# MiniChain

A permissioned blockchain intended to support enterprise‑grade, append‑only logging and asset transfers across tens to hundreds of nodes. Each node maintains a replicated ledger (the blockchain), participates in consensus to order blocks, and enforces validation rules for transactions and blocks. The prototype demonstrates shared global state, synchronization/consistency, and consensus over 3 or more nodes communicating via TCP sockets or RPC. In a larger deployment, MiniChain scales with gossip‑style dissemination, leader rotation, and simple fork‑choice rules.

### development

We have one set of dependencies for all of us, so please create a venv, activate it and then install the requirements when you start the project.
```
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
.\venv\Scripts\activate         # Windows
pip install -r requirements.txt
```
If you want to add requirements, add them first in the venv and then pip freeze them.

```
pip freeze > requirements.txt
```
If you want to see fast if we have a requirement you can for example do 
```
pip list | grep <dependency-name>
```
