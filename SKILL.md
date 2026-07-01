---
name: social-demand-signal-agent
description: Operates a human-reviewed social listening workflow that finds public customer pain, buying intent, product questions, competitor frustration, and unmet demand; routes risk; drafts governed A/B responses; and learns from observed outcomes. Use for social listening, demand-signal monitoring, public conversation discovery, response drafting, outreach review, message experiments, or listening-to-action workflows, including requests framed as monitoring mentions, finding leads, or watching comments.
---

# Social Demand Signal Agent

Turn social listening into reviewed action and measured learning. Keep every outbound response under human control.

## Operating Rules

1. Treat the company profile as the authority for audience, claims, voice, exclusions, escalation, offer, and experiment goals.
2. Never invent missing company policy. Open the local Setup page and help the user complete it before live collection.
3. Use scripts for collection, normalization, deduplication, assignment, storage, and rendering. Use agent judgment for relevance, risk, and writing.
4. Draft both variants while preserving the preassigned experiment variant.
5. Never post, send, or automate a public reply. Present drafts for human approval.
6. Learn only from observed or reviewer-entered events. Never promote a pattern from fixture data.
7. Never request, repeat, display, or write a provider key outside the local credential control.

## Workflow

### 1. Initialize setup

Run:

```bash
python3 scripts/signal_agent.py init
python3 scripts/signal_agent.py serve
```

Use the Setup page to define the company, audience, listening policy, response rules, and experiment. Run `setup-status` or `doctor` when diagnosing readiness. Read [configuration.md](references/configuration.md) for field guidance and migration behavior.

### 2. Collect signals

Choose one provider:

```bash
python3 scripts/signal_agent.py collect --provider json --source /path/to/signals.json
python3 scripts/signal_agent.py collect --provider socialcrawl
```

Live collection requires a ready profile and a locally configured credential. Read [providers.md](references/providers.md) before changing a connector or claiming platform coverage.

### 3. Export and evaluate

Run:

```bash
python3 scripts/signal_agent.py agent-export
```

Read `runtime/agent-batch.json`, [agent-contract.md](references/agent-contract.md), and [governance.md](references/governance.md). Return `draft`, `suppress`, or `escalate` for every signal. For `draft`, produce both variants using only approved claims and the configured disclosure.

Write the response object to `runtime/agent-results.json`, then run:

```bash
python3 scripts/signal_agent.py agent-import --input runtime/agent-results.json
```

### 4. Review and record outcomes

Use the local application to approve only the assigned variant. Record `posted` only after a human posts the response. Record conversion or guardrail events only when observed.

### 5. Analyze learning

Read [experiments.md](references/experiments.md) before changing a response family. Keep findings scoped to message family and platform. Treat `directional` as a lead. Require `validated` status before naming a winner.

## Demo

```bash
python3 scripts/signal_agent.py demo --reset
python3 scripts/signal_agent.py serve
```

Fixture outcomes never affect observed learning.

## Resources

- `scripts/signal_agent.py`: CLI and local server entrypoint.
- `assets/company-profile.schema.json`: profile contract.
- `references/configuration.md`: onboarding and profile migration.
- `references/agent-contract.md`: agent input and output.
- `references/governance.md`: review and safety rules.
- `references/experiments.md`: assignment and learning rules.
- `references/providers.md`: connector and credential contract.
