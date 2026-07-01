# Provider Contract

Every provider must return normalized records with:

- `id`
- `source_type`
- `data_label`
- `platform`
- `source_url`
- `author`
- `published_at`
- `query`
- `text`
- `raw`

## Labels

- `observed`: retrieved from a live source or supplied as real input.
- `fixture`: synthetic data used for tests and demonstrations.

## Current adapters

- `fixture`: Reads a JSON array and labels every record as fixture data.
- `json`: Reads a JSON array or common result envelope and labels records as observed.
- `socialcrawl`: Uses the configured queries and platforms with the live provider endpoint.

The live adapter requires a source URL before a record should be used for public-response review. If a provider returns summaries without verifiable source URLs, retain them for research only or suppress them.

Do not infer that a platform works because it appears in a provider menu. Test current records, timestamps, text, and source URLs before documenting support.
