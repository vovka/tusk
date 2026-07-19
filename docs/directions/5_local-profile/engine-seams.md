# Engine Seams — cloud vs local per slot

Every engine sits behind an existing ABC + factory. Green = exists today, yellow = new
provider class, no kernel/shell changes anywhere.

```mermaid
flowchart TD
    subgraph Slots [LLM slots — per-role env vars]
        GK[gatekeeper · hot path]
        CA[conversation_agent]
        PL[planner_agent]
        EX[executor_agent]
        UT[utility / stop_gate]
    end

    Slots --> F[ConfigurableLLMFactory<br/>parses provider/model]
    F -->|groq/*| G[GroqLLM ✓]
    F -->|openrouter/*| OR[OpenRouterLLM ✓<br/>openai client + base_url]
    F -->|local/*| LO["LocalOpenAILLM (new)<br/>same client shape<br/>→ Ollama / llama.cpp / vLLM"]

    subgraph STT
        SF[STTEngineFactory ✓] -->|groq| GS[GroqSTT ✓ cloud]
        SF -->|whisper| WS[WhisperSTT ✓ local today]
    end

    subgraph TTS
        TF["TTSEngineFactory (new,<br/>mirrors STT factory)"] -->|groq| GT[GroqTTS ✓ cloud]
        TF -->|piper| PT["PiperTTS (new, local)"]
    end

    WS -.-> Transcriber[Transcriber stage — unchanged]
    PT -.-> SP[SpeechPlayback · paplay — already local]

    style LO fill:#fdf3d8,stroke:#b90
    style TF fill:#fdf3d8,stroke:#b90
    style PT fill:#fdf3d8,stroke:#b90
```

The honest intermediate profile the slot system supports today: local STT + local
gatekeeper (speech never leaves the machine), cloud agent slots (actions use cloud LLMs) —
then tighten to fully local as validated models allow.
