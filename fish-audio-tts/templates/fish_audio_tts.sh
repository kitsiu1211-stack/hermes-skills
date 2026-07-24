#!/bin/bash
# Fish Audio TTS wrapper for Hermes custom command provider
# Usage: fish_audio_tts.sh <input_text_file> <output_audio_file>
#
# Replace <YOUR_API_KEY> with your key from https://fish.audio/app/api-keys

API_KEY="<YOUR_API_KEY>"
MODEL="s2.1-pro-free"
ENDPOINT="https://api.fish.audio/v1/tts"

INPUT="$1"
OUTPUT="$2"

if [ ! -f "$INPUT" ]; then
    echo "Error: input file not found: $INPUT" >&2
    exit 1
fi

# JSON-encode the text using Python (handles quotes, newlines, unicode)
TEXT_JSON=$(python3 -c "import json,sys; print(json.dumps(open('$INPUT').read()))")

HTTP_CODE=$(curl -s --max-time 15 -w "%{http_code}" "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -H "model: $MODEL" \
    -d "{\"text\":$TEXT_JSON,\"format\":\"mp3\"}" \
    -o "$OUTPUT" 2>/dev/null)

if [ "$HTTP_CODE" != "200" ]; then
    echo "Error: Fish Audio API returned HTTP $HTTP_CODE" >&2
    cat "$OUTPUT" >&2 2>/dev/null
    exit 1
fi

if [ ! -s "$OUTPUT" ]; then
    echo "Error: empty output file" >&2
    exit 1
fi
