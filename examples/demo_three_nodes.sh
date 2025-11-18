#!/usr/bin/env bash
set -euo pipefail

python -m minichain.cli start N0 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002 &
P0=$!
python -m minichain.cli start N1 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002 &
P1=$!
python -m minichain.cli start N2 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002 &
P2=$!

trap 'kill $P0 $P1 $P2' INT TERM
wait