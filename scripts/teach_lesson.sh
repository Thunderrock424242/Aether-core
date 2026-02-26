#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${AETHER_BASE_URL:-http://127.0.0.1:8765}"
SESSION_ID="${AETHER_SESSION_ID:-dev-player-1}"
LESSON=""

usage() {
  cat <<USAGE
Usage: ./scripts/teach_lesson.sh -l "lesson text" [-s session_id] [-u base_url]

Options:
  -l LESSON      Lesson text to store in A.E.T.H.E.R memory (required)
  -s SESSION_ID  Session id to store lesson under (default: ${SESSION_ID})
  -u BASE_URL    Sidecar base URL (default: ${BASE_URL})
  -h             Show this help

Environment overrides:
  AETHER_BASE_URL   Same as -u
  AETHER_SESSION_ID Same as -s

Examples:
  ./scripts/teach_lesson.sh -l "I'm building NeoForge mods with Gradle"
  ./scripts/teach_lesson.sh -s player-uuid -l "Prefer concise answers"
USAGE
}

while getopts ":l:s:u:h" opt; do
  case "${opt}" in
    l) LESSON="${OPTARG}" ;;
    s) SESSION_ID="${OPTARG}" ;;
    u) BASE_URL="${OPTARG}" ;;
    h)
      usage
      exit 0
      ;;
    :)
      echo "Missing value for -${OPTARG}" >&2
      usage
      exit 1
      ;;
    \?)
      echo "Invalid option: -${OPTARG}" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${LESSON}" ]]; then
  echo "Missing required -l LESSON" >&2
  usage
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed." >&2
  exit 1
fi

TEACH_URL="${BASE_URL%/}/teach"
LEARNING_URL="${BASE_URL%/}/learning/${SESSION_ID}"

payload=$(printf '{"lesson":"%s","session_id":"%s"}' \
  "$(printf '%s' "${LESSON}" | sed 's/\\/\\\\/g; s/"/\\"/g')" \
  "$(printf '%s' "${SESSION_ID}" | sed 's/\\/\\\\/g; s/"/\\"/g')")

echo "Teaching session '${SESSION_ID}' via ${TEACH_URL}"
teach_response=$(curl -fsS -X POST "${TEACH_URL}" \
  -H "Content-Type: application/json" \
  -d "${payload}")

echo "POST /teach response: ${teach_response}"
echo "Current lessons:"
curl -fsS "${LEARNING_URL}"
echo
