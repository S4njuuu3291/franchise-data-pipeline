#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# run-spark-glue.sh — Jalankan Spark/Glue job via Docker AWS Glue Libs
# =============================================================================
# Usage:
#   ./scripts/run-spark-glue.sh                    # default: transform.py
#   ./scripts/run-spark-glue.sh cluster.ipynb      # atau file lain
#   ./scripts/run-spark-glue.sh transform.py --date 2026-05-01
#
# Prerequisites:
#   - Docker installed & running
#   - AWS credentials di ~/.aws/
#   - AWS_PROFILE ter-set (atau default profile)
# =============================================================================

WORKSPACE_LOCATION="$(cd "$(dirname "$0")/.." && pwd)"
GLUE_IMAGE="franchise-glue-custom:latest"

# Default script path (relative to workspace)
DEFAULT_SCRIPT="dags/spark-transform/transform.py"

# Jika argumen pertama hanya nama file (tanpa path), cari di folder default
RAW_SCRIPT="${1:-}"
if [ -z "$RAW_SCRIPT" ]; then
    SCRIPT_FILE_NAME="$DEFAULT_SCRIPT"
elif [[ "$RAW_SCRIPT" != */* ]]; then
    SCRIPT_FILE_NAME="dags/spark-transform/$RAW_SCRIPT"
else
    SCRIPT_FILE_NAME="$RAW_SCRIPT"
fi

PROFILE_NAME="${AWS_PROFILE:-default}"

# Shift arg pertama jika ada
if [ $# -gt 0 ]; then shift; fi

# Build custom Glue image jika belum ada
if ! docker image inspect "$GLUE_IMAGE" >/dev/null 2>&1; then
    echo "🔧 Building custom Glue image ($GLUE_IMAGE)..."
    docker build -t "$GLUE_IMAGE" -f "$WORKSPACE_LOCATION/Dockerfile.glue" "$WORKSPACE_LOCATION"
    echo ""
fi

# Export credentials dari AWS profile untuk S3A Hadoop connector
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
AWS_SESSION_TOKEN=""

AWS_CREDS=$(aws configure export-credentials --profile "$PROFILE_NAME" --format env 2>/dev/null || true)
if [ -n "$AWS_CREDS" ]; then
    eval "$AWS_CREDS"
fi

echo "━━━ Running Glue Spark Job ━━━"
echo "  Image     : $GLUE_IMAGE"
echo "  Workspace : $WORKSPACE_LOCATION"
echo "  Script    : $SCRIPT_FILE_NAME"
echo "  Profile   : $PROFILE_NAME"
echo "  Extra args: $@"
echo ""

docker run -it --rm \
    -v ~/.aws:/home/hadoop/.aws \
    -v "$WORKSPACE_LOCATION":/home/hadoop/workspace/ \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
    -e AWS_DEFAULT_REGION="ap-southeast-1" \
    --name glue5_spark_submit \
    "$GLUE_IMAGE" \
    spark-submit /home/hadoop/workspace/"$SCRIPT_FILE_NAME" "$@"
