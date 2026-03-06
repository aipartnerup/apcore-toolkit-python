# AI-Driven Metadata Enhancement for apcore-toolkit

This document outlines the strategy for using Small Language Models (SLMs) like **Qwen 1.5 (0.6B - 1.7B)** to enhance the metadata extracted by `apcore-toolkit-python`.

## 1. Goal

The toolkit's primary mission is to make existing code "AI-Perceivable". While static analysis (regex, AST) is efficient, it often fails to:
- Generate meaningful `description` and `documentation` for legacy code.
- Create effective `ai_guidance` for complex error handling.
- Infer `input_schema` for functions using `*args` or `**kwargs`.

Using a local SLM allows the toolkit to "understand" the code logic and fill these gaps with high speed and zero cost.

## 2. Architecture: Local LLM Provider (Option B)

To keep `apcore-toolkit-python` lightweight, we **DO NOT** bundle model weights. Instead, we use an OpenAI-compatible local API provider (e.g., Ollama, vLLM, LM Studio).

### Configuration via Environment Variables

The AI enhancement feature is controlled by the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APCORE_AI_ENABLED` | Whether to enable SLM-based metadata enhancement. | `false` |
| `APCORE_AI_ENDPOINT` | The URL of the OpenAI-compatible local API. | `http://localhost:11434/v1` |
| `APCORE_AI_MODEL` | The model name to use (e.g., `qwen:0.6b`). | `qwen:0.6b` |
| `APCORE_AI_THRESHOLD` | Confidence threshold for AI-generated metadata (0-1). | `0.7` |

## 3. Recommended Setup (Ollama)

For the best developer experience, we recommend using [Ollama](https://ollama.com/):

1.  **Install Ollama**.
2.  **Pull the recommended model**:
    ```bash
    ollama run qwen:0.6b
    ```
3.  **Configure environment**:
    ```bash
    export APCORE_AI_ENABLED=true
    export APCORE_AI_MODEL="qwen:0.6b"
    ```

## 4. Enhancement Workflow

When `APCORE_AI_ENABLED` is set to `true`, the `Scanner` will:

1.  **Extract static metadata** from docstrings and type hints.
2.  **Identify missing fields** (e.g., empty `description` or missing `ai_guidance`).
3.  **Send code snippets** to the local SLM with a structured prompt.
4.  **Merge the AI-generated metadata** into the final `ScannedModule`, marking them with a `x-generated-by: "slm"` tag for human audit.

## 5. Security and Privacy

- **No Data Leakage**: Since the model runs locally, your source code never leaves your machine.
- **Auditability**: All AI-generated fields MUST be reviewed by the developer before committing the generated `apcore.yaml`.
