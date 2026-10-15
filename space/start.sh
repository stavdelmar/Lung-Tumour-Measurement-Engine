#!/bin/bash
# Pull the prepared scans + precomputed AI drafts (public RIDER data) from a Hugging Face dataset repo.
set -e
mkdir -p "$ENGINE_DATA" "$ENGINE_STATE"
if [ -n "$ENGINE_DATA_REPO" ]; then
  python - <<'PY'
import os
from huggingface_hub import snapshot_download
d = snapshot_download(os.environ["ENGINE_DATA_REPO"], repo_type="dataset", local_dir="/home/user/data")
print("data ready:", d)
PY
fi
exec uvicorn engine.api:app --host 0.0.0.0 --port 7860
