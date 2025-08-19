#!/bin/bash
PROJECT_DIR="/opt/data/private/liuteng/code/gc-cad-cr/data/input/b001中心区N1区学校"
AGENT_MODEL_NAME="qwen3-8b"
OUTPUT_DIR="/opt/data/private/liuteng/code/dev/gc-cad-cr-server/src/data/tmp/extract_results"

cd /opt/data/private/liuteng/code/dev/gc-cad-cr-server/src

python3 main.py \
  --project_dir "$PROJECT_DIR" \
  --agent_model_name "$AGENT_MODEL_NAME" \
  --output_dir "$OUTPUT_DIR"
