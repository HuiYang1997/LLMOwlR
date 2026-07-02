#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
USE_SYSTEM_SITE_PACKAGES="${USE_SYSTEM_SITE_PACKAGES:-0}"

if [[ ! -d "$VENV_DIR" ]]; then
  if [[ "$USE_SYSTEM_SITE_PACKAGES" == "1" ]]; then
    "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
  else
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
fi

source "$VENV_DIR/bin/activate"
if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt

  if [[ "${INSTALL_RETRIEVAL:-0}" == "1" ]]; then
    python -m pip install -r requirements-retrieval.txt
  fi

  if [[ "${INSTALL_BM25:-0}" == "1" ]]; then
    python -m pip install -r requirements-bm25.txt
  fi
fi

if [[ ! -d BRIGHT ]]; then
  git clone https://github.com/xlang-ai/BRIGHT.git BRIGHT
fi

RUN_GENERATION="${RUN_GENERATION:-1}"
RUN_ANALYSIS="${RUN_ANALYSIS:-1}"
ANALYSIS_INPUT="${ANALYSIS_INPUT:-analyse_result/Qwen3-32B_output.json}"

if [[ "$RUN_GENERATION" == "1" ]]; then
  if [[ -n "${GENERATION_ARGS:-}" ]]; then
    # shellcheck disable=SC2086
    python generateDataset.py $GENERATION_ARGS
  else
    python generateDataset.py \
      --ont data/example.fss \
      --n_just 1 \
      --n_sub 1 \
      --distances 4 \
      --skip_retrieval \
      --subsumption_java_opts "-Xmx2g -Xms512m" \
      --justification_java_opts "-Xmx2g -Xms512m"
  fi
fi

if [[ "$RUN_ANALYSIS" == "1" ]]; then
  python analyse_result/analysis_script.py "$ANALYSIS_INPUT"
fi
