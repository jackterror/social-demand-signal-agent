# Provider Contract

Every provider returns normalized records with `id`, `source_type`, `data_label`, `platform`, `source_url`, `author`, `published_at`, `query`, `text`, and `raw`.

## Current adapters

- `fixture`: Synthetic records for tests and demonstrations.
- `json`: Imported observed records from a JSON array or common result envelope.
- `socialcrawl`: Live search using the configured queries and platform identifiers.

The live adapter requires a source URL before a record enters public-response review. Suppress summaries that cannot be traced to a current source.

## SocialCrawl credential

Create a key through the [SocialCrawl dashboard](https://www.socialcrawl.dev/) and review its [authentication documentation](https://www.socialcrawl.dev/docs/authentication).

The local Setup page stores `SOCIALCRAWL_API_KEY` in `.env`. A process environment value takes precedence. The application reports only whether a key exists and where it came from. It never returns the value to the browser.

The connection test uses SocialCrawl's zero-credit balance endpoint. A successful test proves authentication, not coverage for every configured platform.

Do not claim platform support because a platform appears in a menu. Test current records, timestamps, text, and source URLs before documenting operational support.
