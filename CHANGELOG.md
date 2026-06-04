# Changelog

## Unreleased

- Added an intent gate for `/runtime/context`: LifeOS context is injected only for clear chitchat / companionship turns by default.
- Added optional DeepSeek-based intent classification via `LIFEOS_INTENT_CLASSIFIER=llm`, with deterministic rule fallback.
- Updated connectors to start and finish LifeOS turns only when context was actually injected.
