-- Migration V15: per-user AI provider settings — a user can bring their own
-- OpenAI/Anthropic/Gemini/Ollama key instead of relying solely on the
-- server's shared one. NULL llm_provider means "use the server default",
-- unchanged from today's behavior.
ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_provider TEXT;            -- 'openai' | 'anthropic' | 'gemini' | 'ollama'
ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_api_key_encrypted TEXT;   -- Fernet-encrypted, NULL if unset
ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_base_url TEXT;           -- ollama / custom OpenAI-compatible endpoint
ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_model TEXT;              -- optional model override
