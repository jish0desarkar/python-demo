#!/bin/sh

MODEL="${OLLAMA_MODEL:-phi3:mini}"
# Keep in sync with AVAILABLE_EMBEDDING_MODELS in app/services/llm.py so
# switching EMBEDDING_MODEL does not require a new pull at runtime.
EMBEDDING_MODELS="nomic-embed-text"

ollama serve &
OLLAMA_PID=$!

cleanup() {
  kill "$OLLAMA_PID"
  wait "$OLLAMA_PID"
}

trap cleanup INT TERM

until ollama list >/dev/null 2>&1; do
  sleep 2
done

pull_model_if_missing() {
  MODEL_NAME="$1"

  if [ -z "$MODEL_NAME" ]; then
    return
  fi

  if ! ollama show "$MODEL_NAME" >/dev/null 2>&1; then
    echo "Pulling Ollama model: $MODEL_NAME"
    ollama pull "$MODEL_NAME"
  fi
}

pull_model_if_missing "$MODEL"
for EMB_MODEL in $EMBEDDING_MODELS; do
  pull_model_if_missing "$EMB_MODEL"
done

wait "$OLLAMA_PID"
