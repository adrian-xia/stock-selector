## ADDED Requirements

### Requirement: GeminiClient class
The system SHALL provide a `GeminiClient` class in `app/ai/clients/gemini.py` that wraps the `google-genai` SDK for async communication with Gemini Flash.

The constructor SHALL accept:
- `api_key: str` — Gemini API key
- `model_id: str` — model identifier (default `"gemini-2.0-flash"`)
- `timeout: int` — request timeout in seconds (default `30`)
- `max_retries: int` — retry count on transient errors (default `2`)

#### Scenario: Successful initialization
- **WHEN** `GeminiClient(api_key="valid-key")` is constructed
- **THEN** it SHALL create an internal `google.genai.Client` instance with the provided API key

#### Scenario: Missing API key
- **WHEN** `GeminiClient(api_key="")` is constructed
- **THEN** it SHALL raise `ValueError` with message indicating API key is required

### Requirement: chat method
The `GeminiClient` SHALL provide an async `chat()` method:

```python
async def chat(self, prompt: str, max_tokens: int = 2000) -> str
```

It SHALL:
- Call `client.aio.models.generate_content()` with the specified model
- Set `response_mime_type="application/json"` in generation config to enforce JSON output
- Set `max_output_tokens` from the `max_tokens` parameter
- Return the text content of the response

#### Scenario: Successful chat call
- **WHEN** `await client.chat("Analyze stock 600519.SH")` is called with a valid API key
- **THEN** it SHALL return a non-empty string containing the model's response

#### Scenario: Timeout handling
- **WHEN** the Gemini API does not respond within the configured `timeout` seconds
- **THEN** the method SHALL raise `GeminiTimeoutError`

#### Scenario: API error handling
- **WHEN** the Gemini API returns an error (rate limit, invalid key, server error)
- **THEN** the method SHALL retry up to `max_retries` times with exponential backoff
- **AND** if all retries fail, it SHALL raise `GeminiAPIError` with the original error message

### Requirement: chat_json method
The `GeminiClient` SHALL provide an async `chat_json()` convenience method:

```python
async def chat_json(self, prompt: str, max_tokens: int = 2000) -> dict
```

It SHALL call `chat()` and parse the response as JSON. If JSON parsing fails, it SHALL raise `GeminiResponseParseError`.

#### Scenario: Valid JSON response
- **WHEN** `await client.chat_json(prompt)` is called and the model returns valid JSON
- **THEN** it SHALL return the parsed dict

#### Scenario: Invalid JSON response
- **WHEN** the model returns text that is not valid JSON
- **THEN** it SHALL raise `GeminiResponseParseError` with the raw response text included in the error

### Requirement: Custom exception classes
The system SHALL define the following exception classes in `app/ai/clients/gemini.py`:
- `GeminiError` — base exception for all Gemini client errors
- `GeminiTimeoutError(GeminiError)` — request timeout
- `GeminiAPIError(GeminiError)` — API-level errors (rate limit, auth, server)
- `GeminiResponseParseError(GeminiError)` — response JSON parse failure

#### Scenario: Exception hierarchy
- **WHEN** a `GeminiTimeoutError` is raised
- **THEN** it SHALL be catchable as both `GeminiTimeoutError` and `GeminiError`

### Requirement: Token usage tracking
The `GeminiClient` SHALL provide a `get_last_usage()` method that returns token usage from the most recent API call:

```python
def get_last_usage(self) -> dict[str, int]
```

Returns `{"prompt_tokens": N, "completion_tokens": M, "total_tokens": N+M}`. Returns `{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}` if no call has been made.

#### Scenario: Usage after successful call
- **WHEN** `chat()` completes successfully
- **THEN** `get_last_usage()` SHALL return the token counts from that call
