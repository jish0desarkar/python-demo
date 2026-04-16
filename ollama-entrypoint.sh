#!/bin/sh

MODEL="${OLLAMA_MODEL:-phi3:mini}"
EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-}"

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
pull_model_if_missing "$EMBEDDING_MODEL"

wait "$OLLAMA_PID"
