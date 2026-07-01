# Company Profile

Complete the guided Setup page before a live run. The application saves progress with `profile_status: setup` and changes it to `ready` only after every required decision validates.

## Required decisions

- `company`: Name the company, industry, product, website, and factual description.
- `audience`: Describe who has the problem and the phrases they use for pain and active intent.
- `offer`: Define one honest next step and its destination URL.
- `voice`: List concrete writing attributes.
- `disclosure`: Write the affiliation sentence used in every response.
- `claims`: Separate approved statements from forbidden statements.
- `safety`: List irrelevant contexts, specialist-review topics, and the per-author frequency limit.
- `listening`: Define queries, platforms, freshness, and run size.
- `response_families`: Group signals that share one message hypothesis.
- `experiment`: Name the conversion and guardrail events, then set a sample minimum.

Use exact customer phrases. `Productivity problems` will collect noise. `Manually reconciling invoices every Friday` gives both the deterministic prefilter and the agent useful evidence.

Approved claims must be verifiable. Forbidden claims should cover guarantees, unsupported comparisons, and language the company cannot defend.

## Profile states

- `setup`: Progress is saved, but live listening is blocked.
- `demo`: Synthetic fixture data can run without a provider key.
- `ready`: The profile passed validation and can support JSON or live collection.

## Migration and portability

Profiles carry `schema_version`. When a new required field is introduced, the application writes a local backup, migrates the structure, and returns the profile to Setup for confirmation.

Use `profile-export` and `profile-import` to move policy between installations. Provider credentials never enter the profile.
