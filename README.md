# farmconnect

A WhatsApp-based matchmaking service connecting farmers and buyers.

## Setup

1. Ensure you have an environment file (e.g. `.env` or whatever you've
   renamed the example to) in the project root; it must contain the variables
   listed below.
2. Install dependencies.  If you're using `uv` package manager run:

```bash
uv add <package>  # e.g. uv add fastapi celery ...
```

Alternatively you can still use pip:

```bash
pip install -e .
```

3. Initialize the database:

```bash
python -m app.database.initialize
```

## Running the application

Start the API server:

```bash
python main.py
```

Start a Celery worker (from workspace root):

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info
```

## Development notes

- Use Pydantic models for configuration and data validation.
- All logic may be triggered via the `/webhooks/whatsapp` endpoint.  
  The server expects a header `x-api-key` matching `WHATSAPP_VERIFY_TOKEN` for basic security.

### Message Flow for Multiple Users

The bot supports multiple concurrent users with the following workflow:

1. **User sends a message** – Any farmer or buyer sends their first message to the bot
2. **Initial greeting** – Bot immediately replies with "Hello this is FarmConnect!"
3. **Agent processing** – Guardrail, Intent, and Extraction agents process the message
4. **User & Listing storage** – User profile and listing/buyer request are persisted to the database
5. **Automatic matching** – System attempts to match the user with existing listings or buyer requests
6. **Confirmation flow** – When matches are found, users can reply "YES" to receive contact numbers

- Incoming messages are validated and stored using SQLAlchemy.  
  When a buyer or farmer message is processed, the system attempts to match them and stores
  a `Match` row; users can reply `YES` to receive contact numbers for their matches.
- Agents (guardrail/intent/extract) extend `BaseAgent` for modular processing.
- The WhatsApp service is async and scalable, using httpx for concurrent HTTP requests.

## Exposing locally with ngrok

1. Install [ngrok](https://ngrok.com/) and authenticate (`ngrok authtoken <token>`).
2. Run your FastAPI app on port 8000 as described earlier.
3. In another terminal execute:

   ```bash
   ngrok http 8000
   ```
> **Running modules**  Avoid invoking source files inside `app/` directly (e.g.
> `python app/services/whatsapp_service.py`).  Either install the package with
> `pip install -e .` or run modules via the `-m` flag from the project root
> (`python -m app.services.whatsapp_service`).  A path hack in some scripts
> allows quick tests, but proper package context is preferred.
4. Use the HTTP forwarding URL provided by ngrok as the webhook URL in the Meta/WhatsApp
   developer dashboard.

> **Tip:** add `NGROK_AUTHTOKEN` to `.env` and include instructions if you need to launch
> programmatically.

## Security

- The webhook checks a simple API key header.  In production you may want to switch to
  more robust authentication (HMAC verification, OAuth, etc.).
- Avoid logging sensitive information.  Use SSL/HTTPS in production.
- Consider rate‑limiting incoming requests and verifying source IPs.

## Future improvements

1. **Improved matching** – add geolocation, quantity balance, manual approval, etc.
2. **State management** – keep track of conversation phases to handle confirmations
   more gracefully, perhaps with a session table or Redis.
3. **Retry and error handling** – make Celery tasks idempotent and add logging/monitoring.
4. **Prompt tweaking** – refine Jinja templates, add more fields, handle edge cases.
5. **Migrations** – integrate Alembic or similar once schema evolves beyond simple additions.
6. **Web UI or dashboard** – allow farmers/buyers to view/manage their listings and matches.
7. **Testing** – expand coverage, especially for database matching and LLM responses.
8. **Container security** – use non‑root user, secrets management, and secure network policies.

## Linking the pieces

The project ties together:

- **FastAPI** for HTTP handling and webhook entry point
- **Celery + Redis** for asynchronous message processing
- **SQLAlchemy** for data models and matching logic
- **Pydantic & prompts** for validated I/O to LLMs
- **OpenAI / Ollama** as backend LLMs via a unified service
- **Docker/compose** for running everything locally or in containers
- **Ngrok** for exposing the local server to the internet during development

With the structure above, extending or replacing components (e.g. swapping LLM,
adding a frontend, migrating database) is straightforward thanks to clear boundaries.

---

We aim for **simple but perfect code**, so feel free to refactor further as needed.
