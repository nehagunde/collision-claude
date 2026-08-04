#!/usr/bin/env bash
# Phase 0 verification for the NH16 collision-warning project.
# Run this INSIDE the Kali VM, then paste the full output back.
#
# If your ns-3-dev checkout lives somewhere other than ~/ns-3-dev,
# set NS3_DIR before running, e.g.:
#   NS3_DIR=/opt/ns-3-dev ./verify_setup.sh

set -u
NS3_DIR="${NS3_DIR:-$HOME/ns-3-dev}"

echo "=== SUMO ==="
if command -v sumo >/dev/null 2>&1; then
    sumo --version | head -n 2
else
    echo "sumo: NOT FOUND on PATH"
fi

echo
echo "=== Python 3 ==="
if command -v python3 >/dev/null 2>&1; then
    python3 --version
else
    echo "python3: NOT FOUND"
fi

echo
echo "=== NS-3 ==="
if [ -x "$NS3_DIR/ns3" ]; then
    echo "Found ns3 wrapper at: $NS3_DIR/ns3"
    (cd "$NS3_DIR" && ./ns3 --version 2>&1 | head -n 5)
elif command -v ns3 >/dev/null 2>&1; then
    ns3 --version | head -n 5
else
    echo "ns3: NOT FOUND at $NS3_DIR or on PATH (set NS3_DIR if it's elsewhere)"
fi

echo
echo "=== WAVE / 802.11p module (needed for Phase 3) ==="
if [ -d "$NS3_DIR/src/wave" ]; then
    echo "Found: $NS3_DIR/src/wave"
elif [ -d "$NS3_DIR/src/wifi" ]; then
    echo "wave/ module not found, but src/wifi/ exists (wave depends on wifi being present)"
else
    echo "Neither src/wave nor src/wifi found under $NS3_DIR — check NS3_DIR is correct"
fi

echo
echo "=== Python libraries (requirements.txt) ==="
for pkg in traci sumolib pandas matplotlib numpy; do
    if python3 -c "import $pkg" >/dev/null 2>&1; then
        echo "$pkg: OK"
    else
        echo "$pkg: MISSING (pip install -r requirements.txt)"
    fi
done

echo
echo "=== Shared folder mount check ==="
if [ -d "$HOME/collision_claude" ]; then
    echo "Found $HOME/collision_claude -> $(ls -la "$HOME/collision_claude" | head -n 5)"
else
    echo "$HOME/collision_claude not found — confirm the VMware shared-folder mount path for this project"
fi
