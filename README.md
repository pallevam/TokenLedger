# 🪙 TokenLedger

> A self-hosted tracker for your LLM token usage and costs across frontier models — built for OSS developers who want full visibility into their AI spending.

---

## Why?

If you use multiple LLM APIs (OpenAI, Anthropic, Gemini) for personal projects, prototyping, or side work, the vendor dashboards are siloed, hard to compare, and don't give you a unified view. **TokenLedger** solves this:

- 📊 **One dashboard** — see all token usage and costs side by side
- 💸 **Know your spend** — real-time cost estimates based on current pricing
- 🔐 **Secure by design** — keys are fetched from GCP Secret Manager at runtime, never hardcoded
- 🧩 **Pluggable** — new providers and models are trivially addable (SOLID interfaces)
- 🗄️ **Self-hosted** — Supabase/PostgreSQL, migrate to cloud when you're ready

---

## Supported Providers & Models

| Provider  | Models Tracked                              | Token Counting Method    |
|-----------|---------------------------------------------|--------------------------|
| OpenAI    | `gpt-4`, `gpt-3.5-turbo`, and variants     | `tiktoken` (exact)       |
| Anthropic | `claude-3-opus`, `claude-3-sonnet`, etc.   | Word estimate (TODO: SDK)|
| Google    | `gemini-1.5-pro`, `gemini-1.0-pro`, etc.  | Word estimate (TODO: SDK)|

---

## Architecture

```
token_tracker/
├── src/
│   ├── core/               # Interfaces + TokenTracker orchestrator
│   │   ├── interfaces.py   # ITokenizer, IProviderPricing, ITrackerStorage, ISecretManager
│   │   ├── tracker.py      # Main TokenTracker class
│   │   └── README.md
│   ├── tracker/            # Token counting and cost calculation
│   │   ├── tokenizers.py   # Tiktoken (OpenAI), stub tokenizers
│   │   └── pricing.py      # Per-model cost rates
│   ├── storage/            # SQLAlchemy models + Postgres/SQLite storage
│   │   ├── models.py
│   │   ├── database.py
│   │   └── README.md
│   ├── security/           # GCP Secret Manager + local env fallback
│   │   ├── gcp_secret_manager.py
│   │   └── README.md
│   └── api/
│       └── main.py         # FastAPI server + Jinja dashboard routes
├── templates/
│   └── dashboard.html      # Dark-mode usage dashboard
├── requirements.txt
├── .gitignore
└── README.md               # ← you are here
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/pallevam/TokenLedger.git
cd TokenLedger
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure (Local Dev)

For local development, create a `.env` file (it's gitignored):

```bash
cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=sqlite:///./tracker.db   # or your Supabase/PostgreSQL URL
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...
```

> **Production**: Set `GOOGLE_CLOUD_PROJECT=your-gcp-project-id` and store keys in GCP Secret Manager instead.  
> See [`src/security/README.md`](src/security/README.md) for GCP setup steps.

### 3. Run the Dashboard

```bash
uvicorn src.api.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to see your dashboard.

---

## Usage: Tracking a Request

```python
from src.core.tracker import TokenTracker

tracker = TokenTracker()

record = tracker.track_request(
    user_id="vamsi",
    provider="openai",
    model="gpt-4",
    prompt="Explain transformers in one paragraph.",
    response_text="Transformers are...",
    latency_ms=320
)

print(f"Cost: ${record.total_cost:.6f} | Tokens: {record.prompt_tokens}p / {record.completion_tokens}c")
```

---

## Adding a New Provider

1. **Add a tokenizer** in `src/tracker/tokenizers.py` implementing `ITokenizer`.
2. **Add pricing rates** in `src/tracker/pricing.py` under `SimplePricing.PRICING`.
3. **Register the tokenizer** in `src/core/tracker.py` `_tokenizers` dict.
4. **Add the secret** to GCP Secret Manager with the name `{provider}_api_key`.

No existing code needs to change — open/closed in practice.

---

## Secrets Management (Production)

Keys are **never** stored in plain text or committed to git.

In production, create secrets in GCP:

```bash
echo -n "sk-..." | gcloud secrets create openai_api_key --data-file=-
echo -n "sk-ant-..." | gcloud secrets create anthropic_api_key --data-file=-
echo -n "AI..." | gcloud secrets create gemini_api_key --data-file=-
```

Grant the service account running the app `roles/secretmanager.secretAccessor` on each secret.

---

## Database (Supabase / PostgreSQL)

The `DATABASE_URL` can point to:
- A **local SQLite file** (default, great for personal dev)
- A **self-hosted Supabase PostgreSQL** instance (`postgresql://...`)
- Any other PostgreSQL-compatible connection string

Tables are auto-created on startup via SQLAlchemy.

---

## Contributing

This project is primarily built for personal use but PRs welcome!  
If you find value in this and want to contribute a new provider or feature, please open an issue first.

---

## License

MIT — use it, fork it, extend it.
