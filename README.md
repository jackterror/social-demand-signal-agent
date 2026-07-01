# Social Demand Signal Agent

An agentic social listening system that finds customer pain and buying intent, drafts human-reviewed A/B responses, and learns from tracked outcomes.

## What it does

People describe problems, compare options, and ask for help in public. Social Demand Signal Agent helps a team act while that need is still present.

It moves each qualified signal through one controlled loop:

`listen -> qualify -> route -> draft A/B -> human review -> respond -> measure -> learn`

The system can:

- listen for customer pain, buying intent, product questions, competitor frustration, and unmet demand
- collect public posts and comments through pluggable providers
- normalize, deduplicate, score, and route each signal
- separate response opportunities from risk, noise, and escalation cases
- draft two governed response variants from company-approved claims
- assign the experiment variant before outcomes exist
- require human approval before any response is posted
- record observed outcomes in a local database
- report learning within each message family and platform

## Why it exists

A social listening dashboard can show what people said. A response generator can supply copy.

On their own, neither handles the work between signal and learning. A useful signal still needs to be checked, routed, answered, approved, tracked, and turned into learning.

This project connects that work without giving an agent permission to post. Signals stay grounded in public source data. Risky cases move to suppression or escalation. Humans control every response. The system learns only from outcomes that were observed or entered by a reviewer.

## Primary entrypoints

- `SKILL.md` is the primary entrypoint for Agent Skills-compatible clients.
- `scripts/signal_agent.py` is the deterministic runtime and CLI entrypoint.

## Quick start

Requires Python 3.11 or newer. The core application uses only the Python standard library.

```bash
git clone https://github.com/jackterror/social-demand-signal-agent.git
cd social-demand-signal-agent
python3 scripts/signal_agent.py init
```

Edit `runtime/company-profile.json`, replace every onboarding field, and set `profile_status` to `ready`.

```bash
python3 scripts/signal_agent.py validate
python3 scripts/signal_agent.py collect --provider json --source /path/to/signals.json
python3 scripts/signal_agent.py agent-export
```

Ask your agent to use `SKILL.md`, process `runtime/agent-batch.json`, and write `runtime/agent-results.json`.

```bash
python3 scripts/signal_agent.py agent-import --input runtime/agent-results.json
python3 scripts/signal_agent.py serve
```

Open `http://127.0.0.1:8766`.

## Fixture demo

```bash
python3 scripts/signal_agent.py demo --reset
python3 scripts/signal_agent.py serve
```

The demo uses labeled fixture data. Fixture outcomes never contribute to observed experiment learning.

## Agent Skill installation

The repository root is compatible with the [Agent Skills specification](https://agentskills.io/specification). Clone or link the folder into the skills directory used by your client.

Claude Code:

```bash
ln -s /absolute/path/social-demand-signal-agent ~/.claude/skills/social-demand-signal-agent
```

OpenAI Codex:

```bash
ln -s /absolute/path/social-demand-signal-agent ~/.codex/skills/social-demand-signal-agent
```

Then ask:

```text
Use $social-demand-signal-agent to find public customer pain, draft governed A/B responses, and build a human-reviewed learning loop for my company.
```

## Core workflow

1. Define the company, audience, pain signals, claims, voice, offer, risk rules, and experiment goals.
2. Validate the profile before any live collection can run.
3. Collect fixture, JSON, or live provider records.
4. Apply deterministic exclusions, relevance scoring, and stable A/B assignment.
5. Export qualified signals to the host agent for contextual judgment and writing.
6. Import `draft`, `suppress`, and `escalate` decisions.
7. Approve, edit, reject, or escalate each response in the local review application.
8. Record posting, primary outcomes, and guardrail events.
9. Review learning within each message family and platform.

## Recommended use case

Use this system when:

- customers discuss a recognizable problem in public
- timing affects whether a response is useful
- the company has a clear offer and approved claims
- a person can review every outbound response
- the team wants to learn from customer action, not raw engagement

It can support growth, community, customer success, founder-led sales, and product teams. It is not a replacement for consent, platform policy, or company-specific review.

## Architecture

```text
social-demand-signal-agent/
|-- SKILL.md
|-- README.md
|-- PACKAGE-DESCRIPTION.md
|-- CREATOR.md
|-- SOURCES.md
|-- CONTRIBUTING.md
|-- SECURITY.md
|-- scripts/
|   |-- signal_agent.py
|   |-- package_release.py
|   |-- release_audit.py
|   `-- sdsa/
|-- references/
|-- assets/
|   |-- company-profile.example.json
|   |-- company-profile.schema.json
|   |-- fixtures/
|   `-- local application files
|-- agents/openai.yaml
|-- evals/
`-- tests/
```

The host agent handles contextual judgment, classification, and writing. Deterministic scripts handle collection, normalization, deduplication, assignment, validation, persistence, and rendering.

Operational state stays local in SQLite. The local application binds to `127.0.0.1` and does not post responses.

## Configuration

Every installation defines its own:

- company and product
- audience, pain points, and intent signals
- offer and CTA
- voice and disclosure
- approved and forbidden claims
- exclusions, escalation terms, and per-author frequency limits
- queries, platforms, freshness, and run size
- response families and hypotheses
- primary and guardrail events

Live collection is blocked until the profile is complete and marked `ready`.

## Providers

- Fixture JSON for offline demos and tests
- Generic JSON import
- SocialCrawl live search

Set `SOCIALCRAWL_API_KEY` in the environment for live collection. Provider availability and platform coverage can change. Verify current records, timestamps, text, and source URLs before operational use.

## Experiment logic

- Variant assignment is stable and occurs before drafting or outcomes.
- Reviewers approve the assigned variant instead of choosing an arm.
- `posted` is the exposure denominator.
- Fixture events are excluded from real results.
- A leader remains directional until both arms meet the configured sample minimum.
- A winner requires separated Wilson intervals and a stable guardrail rate.
- Learning stays scoped to message family and platform context.

## Safety boundaries

- No autonomous posting or direct messages
- No concealed affiliation
- No unsupported or forbidden claims
- No public collection of private details
- No learning from fixture outcomes
- No response to escalated or suppressed signals
- No assumption that every public complaint is an outreach opportunity
- No response beyond the configured 24-hour per-author limit

## Testing

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_audit.py .
python3 scripts/package_release.py
```

The test and eval suites cover configuration, providers, normalization, deduplication, routing, assignment, persistence, browser states, skill triggering, governed drafting, and experiment interpretation.

## Limitations

- Live platform coverage depends on the configured provider.
- The system does not post responses.
- The local server is intended for one trusted user on `127.0.0.1`.
- Outcome events are manually recorded unless the installer connects a first-party analytics source.
- Regulated or sensitive uses require company-specific policy and specialist review.

## Creator and license

Created by [Jack Dalrymple](https://www.jackdalrymple.com/), Founder of [Cap & Cut](https://capandcut.com/). See [CREATOR.md](CREATOR.md) for project context.

Released under the MIT License. See [LICENSE](LICENSE).
