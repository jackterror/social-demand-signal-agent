# Social Demand Signal Agent

An agentic social listening system that finds customer pain and buying intent, drafts human-reviewed A/B responses, and learns from tracked outcomes.

## What it does

People describe problems, compare options, and ask for help in public. Social Demand Signal Agent helps a team act while that need is still present.

`listen -> qualify -> route -> draft A/B -> human review -> respond -> measure -> learn`

The system can:

- listen for customer pain, buying intent, product questions, competitor frustration, and unmet demand
- collect public posts and comments through pluggable providers
- normalize, deduplicate, score, and route each signal
- separate response opportunities from noise, risk, and escalation
- draft two response variants from company-approved claims
- assign the experiment variant before outcomes exist
- require human approval before any response is posted
- record observed outcomes in a local SQLite database
- report learning within each message family and platform

## Why it exists

A social listening dashboard can show what people said. A response generator can supply copy.

On their own, neither handles the work between signal and learning. A useful signal still needs to be checked, routed, answered, approved, tracked, and turned into evidence.

This project connects that work without giving an agent permission to post. Risky cases move to suppression or escalation. Humans control every response. The system learns only from outcomes that were observed or entered by a reviewer.

## Quick start

Requires Python 3.11 or newer. The application uses the Python standard library.

```bash
git clone https://github.com/jackterror/social-demand-signal-agent.git
cd social-demand-signal-agent
python3 scripts/signal_agent.py init
python3 scripts/signal_agent.py serve
```

Open `http://127.0.0.1:8766` if the browser does not open automatically.

The Setup page walks through:

1. Company, industry, product, and website
2. Audience, pain points, intent signals, queries, and platforms
3. Offer, voice, disclosure, claims, exclusions, and escalation rules
4. Message families, A/B hypotheses, and outcome events
5. SocialCrawl credential storage and connection testing

Live listening remains blocked until the company profile is complete and a provider credential is configured. Progress can be saved at any point.

## SocialCrawl setup

Create a key from the [SocialCrawl dashboard](https://www.socialcrawl.dev/) and follow its [authentication guide](https://www.socialcrawl.dev/docs/authentication). The local Setup page saves the key to `.env`, restricts file permissions where supported, and never returns the value to the browser.

Process environment values take precedence over `.env`. A process-provided key cannot be removed from the dashboard.

Check readiness without exposing the key:

```bash
python3 scripts/signal_agent.py setup-status
python3 scripts/signal_agent.py doctor
```

## Fixture demo

Use the demo without a provider account:

```bash
python3 scripts/signal_agent.py demo --reset
python3 scripts/signal_agent.py serve
```

Fixture records and outcomes are labeled and excluded from observed experiment learning.

## Agent Skill installation

The repository root follows the [Agent Skills specification](https://agentskills.io/specification).

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
Use $social-demand-signal-agent to set up a human-reviewed social listening and response-learning workflow for my company.
```

## Core workflow

1. Complete and confirm the company-owned listening profile.
2. Collect fixture, JSON, or live provider records.
3. Apply deterministic exclusions, relevance scoring, and A/B assignment.
4. Export qualified signals to the host agent for contextual judgment and writing.
5. Import `draft`, `suppress`, and `escalate` decisions.
6. Approve, edit, reject, or escalate each response locally.
7. Record posting, conversion, and guardrail events.
8. Review learning within each message family and platform.

## Profile portability

Profiles contain company policy but never provider credentials.

```bash
python3 scripts/signal_agent.py profile-export --output company-profile.json
python3 scripts/signal_agent.py profile-import --input company-profile.json
```

Profiles carry a schema version. The application backs up an older profile before migrating it and returns the profile to Setup when new required decisions need confirmation.

## Architecture

```text
social-demand-signal-agent/
|-- SKILL.md
|-- scripts/sdsa/       deterministic runtime
|-- references/         agent and operator contracts
|-- assets/             local application and fixtures
|-- docs/images/        release visuals
|-- agents/openai.yaml  client metadata
|-- evals/              trigger and functional evals
`-- tests/              unit, integration, server, and release checks
```

The host agent handles contextual judgment, classification, and writing. Scripts handle collection, normalization, deduplication, assignment, validation, persistence, and rendering.

## Experiment logic

- Assignment is stable and occurs before drafting or outcomes.
- Reviewers approve the assigned variant instead of choosing an arm.
- `posted` is the exposure denominator.
- Fixture events are excluded from real results.
- A leader remains directional until both arms meet the sample minimum.
- A winner requires separated Wilson intervals and a stable guardrail rate.
- Learning stays scoped to message family and platform.

## Safety boundaries

- No autonomous posting or direct messages
- No concealed affiliation
- No unsupported or forbidden claims
- No response to escalated or suppressed signals
- No learning from fixture outcomes
- No credentials in profiles, databases, browser storage, logs, or archives
- No response beyond the configured per-author frequency limit
- Local server restricted to loopback addresses with same-origin mutation controls

## Testing

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_audit.py .
python3 scripts/package_release.py
```

The suite covers onboarding, migration, credentials, provider contracts, routing, assignment, persistence, review, experiment interpretation, security boundaries, and release packaging.

Generate credential-free release screenshots and the GitHub social preview with:

```bash
npm install
npx playwright install chromium
npm run capture
```

## Limitations

- Live coverage depends on the provider's current endpoints and returned source URLs.
- The system does not post responses.
- The local server is intended for one trusted user.
- Outcome events are manual unless the installer connects first-party analytics.
- Regulated or sensitive uses require company policy and specialist review.

## Creator and license

Created by [Jack Dalrymple](https://www.jackdalrymple.com/), Founder of [Cap & Cut](https://capandcut.com/). See [CREATOR.md](CREATOR.md).

Released under the MIT License. See [LICENSE](LICENSE).
