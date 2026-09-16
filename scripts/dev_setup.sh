#!/usr/bin/env bash
# Novu Opportunity Radar — Development Environment Setup Script (Linux / macOS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "==============================================="
echo " Novu Opportunity Radar — Dev Setup"
echo "==============================================="

echo ""
echo "[1/4] Installing Python requirements..."
cd "$BACKEND_DIR"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created backend/.env from .env.example"
fi
python3 -m pip install -r requirements.txt

echo ""
echo "[2/4] Applying database migrations..."
python3 manage.py migrate

echo ""
echo "[3/4] Seeding demonstration dataset & users..."
python3 manage.py seed_demo

echo ""
echo "[4/4] Setting up frontend dependencies..."
cd "$FRONTEND_DIR"
npm install

cd "$PROJECT_ROOT"
echo ""
echo "Setup complete! Run ./scripts/demo_run.sh to start services."
