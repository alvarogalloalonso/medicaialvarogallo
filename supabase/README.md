# Optional audio transcription experiment

Not deployed or tested against a live service in this revision. Disabled in the React presentation unless `VITE_ENABLE_AUDIO=true` is explicitly set.

Configure project URL/publishable key, an authenticated Supabase user session, `OPENAI_API_KEY` on the server and an explicit comma-separated `ALLOWED_ORIGINS` allowlist. JWT verification and `auth.getUser` are required; the publishable project key alone is not user authentication. The frontend contains no complete user-login flow for this experiment.

Request bodies are bounded to approximately 2 MiB decoded audio; the upstream call has a 30-second timeout. Audio/transcripts/upstream errors are not logged. A configured local transcription endpoint fails locally instead of silently sending audio to a hosted fallback.

Use fictional audio only. A hosted service would still need persistent per-user rate limiting, retention rules and deployment review; none is provided here.
