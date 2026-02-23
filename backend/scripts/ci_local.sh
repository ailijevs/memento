#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${VENV_DIR:-.venv-ci}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN not found. Install Python 3.11 or set PYTHON_BIN."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [[ "$SKIP_INSTALL" != "1" ]]; then
  python -m pip install --disable-pip-version-check --upgrade pip
  python -m pip install --disable-pip-version-check -r requirements.txt
fi

export SUPABASE_URL="${SUPABASE_URL:-https://test.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-test-anon-key}"
export SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-test-service-role-key}"
export SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET:-test-jwt-secret-for-ci-testing-only}"
export APP_NAME="${APP_NAME:-Memento API Test}"
export DEBUG="${DEBUG:-true}"

echo "==> flake8"
flake8 app/ tests/

echo "==> isort check"
isort --check-only --diff app/ tests/

echo "==> black check"
black --check --diff app/ tests/

echo "==> mypy"
mypy --config-file=pyproject.toml app/ tests/

echo "==> pytest (quick)"
python -m pytest tests/ -v --tb=short

echo "==> pytest (coverage)"
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=50

echo "==> import/build checks"
python -c "from app.main import app; print('App created successfully')"
python -c "import app.api, app.auth, app.db, app.dals, app.schemas; print('All modules import successfully')"

echo "Local CI checks passed."
