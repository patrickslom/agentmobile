# Title + Summary Plan

## Goal
Generate a clear chat title and short summary from the first 2 exchanges so conversation history is easy to scan.

## Definitions
- Exchange = one user message + one assistant response.
- Input window = first 2 exchanges of a conversation (up to 4 messages total).

## Behavior
1. After enough early messages are available, agent generates:
   - `title`
   - `summary_short`
2. Save both values on the conversation record.
3. Use them in chat history/sidebar list.
4. Allow regeneration if early context changes significantly.

## Output Constraints
### Title
- 3-8 words preferred.
- Specific and actionable.
- No generic titles like "New Chat" unless fallback is required.

### Short Summary
- 1 sentence.
- About 12-24 words.
- Focus on user intent and current work scope.

## Trigger Strategy
- Primary trigger: when conversation reaches 2 exchanges.
- Early trigger (optional): after 2-3 exchanges if confidence is high.
- Regeneration trigger:
  - explicit user action ("rename/regenerate summary")
  - major scope shift detected in early thread state

## Fallback Rules
- If fewer than 2 exchanges exist:
  - keep temporary default title.
  - defer summary generation.
- If generation fails:
  - keep existing title/summary.
  - retry asynchronously.

## Data Model Direction
Add/confirm conversation fields:
- `title` (already present)
- `summary_short` (new nullable text/varchar)
- `title_generated_at` (nullable timestamp)
- `summary_generated_at` (nullable timestamp)

## UI Usage
- Sidebar/chat history row should show:
  - title (primary line)
  - short summary (secondary line, truncated)
  - updated timestamp

## Quality Guardrails
- Do not include secrets/tokens in title/summary.
- Avoid personal data beyond what is needed for recognition.
- Keep wording neutral and factual.

## Example
- Title: `Set Up R2 File Storage`
- Summary: `Configured optional Cloudflare R2 integration and planned local fallback behavior for uploads on VPS deployments.`
