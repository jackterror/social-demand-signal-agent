# Company Profile

Complete the profile before a live run. Keep `profile_status` set to `demo` while testing, then change it to `ready` after a human confirms every field.

## Required decisions

- `company`: State the company, product, and factual description.
- `audience`: Describe who has the problem. Add phrases they use for pain and active intent.
- `offer`: Define one honest next step and its destination URL.
- `voice`: List concrete writing attributes.
- `disclosure`: Write the affiliation sentence used in every response.
- `claims`: Separate approved statements from forbidden statements.
- `safety`: List irrelevant contexts, specialist-review topics, and the maximum responses allowed per author in 24 hours.
- `listening`: Define queries, platforms, freshness, and run size.
- `response_families`: Group signals that share one message hypothesis.
- `experiment`: Name the business event and guardrail event, then set a minimum sample size.

## Configuration standard

Use exact phrases where possible. A broad pain point such as `productivity problems` will collect noise. A phrase such as `manually reconciling invoices every Friday` gives the prefilter and agent useful evidence.

Approved claims must be verifiable. Forbidden claims should cover guarantees, unsupported comparisons, and language the company cannot defend.

Do not put API keys in the profile. Use environment variables.
