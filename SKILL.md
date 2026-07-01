---
name: social-demand-signal-agent
description: Operates a human-reviewed social listening workflow that finds public customer pain, buying intent, product questions, competitor frustration, and unmet demand; routes risk; drafts governed A/B responses; and learns from observed outcomes. Use when a user wants social listening, demand-signal monitoring, public conversation discovery, response drafting, outreach review, message experiments, or a listening-to-action workflow, even when they describe it as monitoring mentions, finding leads, or watching comments.
---

# Social Demand Signal Agent

Turn social listening into reviewed action and measured learning. Keep every outbound response under human control.

## Operating Rules

1. Treat the company profile as the authority for audience, claims, voice, exclusions, escalation, offer, and experiment goals.
2. Never invent missing company policy. Run `init`, ask the user to complete the profile, and validate it before collecting live data.
3. Use scripts for collection, normalization, deduplication, assignment, storage, and rendering. Use agent judgment for relevance, risk, and response writing.
4. Draft both variants, but preserve the preassigned variant for the experiment. Do not select the variant based on which draft sounds better.
5. Do not post, send, or automate a public reply. Present drafts for human approval.
6. Learn only from observed or reviewer-entered events. Never promote a pattern from fixture data.

## Workflow

### 1. Initialize and validate

Run:

```bash
python3 scripts/signal_agent.py init
python3 scripts/signal_agent.py validate
```

If validation fails, help the user complete `runtime/company-profile.json`. Read [configuration.md](references/configuration.md) when defining the profile or adding an industry policy.

### 2. Collect signals

Choose one provider:

```bash
python3 scripts/signal_agent.py collect --provider fixture --source assets/fixtures/signals.json
python3 scripts/signal_agent.py collect --provider json --source /path/to/signals.json
python3 scripts/signal_agent.py collect --provider socialcrawl
```

Live collection requires `profile_status: ready` and `SOCIALCRAWL_API_KEY`. Read [providers.md](references/providers.md) when changing a connector or normalizing a new payload.

### 3. Export the agent batch

Run:

```bash
python3 scripts/signal_agent.py agent-export
```

Read `runtime/agent-batch.json`, [agent-contract.md](references/agent-contract.md), and [governance.md](references/governance.md). Evaluate every exported signal. Return `draft`, `suppress`, or `escalate`. For `draft`, produce both required variants using only approved claims and the configured disclosure.

Write the exact response object to `runtime/agent-results.json`, then run:

```bash
python3 scripts/signal_agent.py agent-import --input runtime/agent-results.json
```

### 4. Review and record outcomes

Start the local application:

```bash
python3 scripts/signal_agent.py serve
```

Approve only the assigned variant, with edits if needed. Record `posted` only after a human posts the response. Record the configured primary or guardrail event only when it is observed.

### 5. Analyze learning

Read [experiments.md](references/experiments.md) before recommending a winner or changing a response family. Keep findings scoped to message family and platform. Treat `directional` as a lead, not proof. Require `validated` status before naming a winner.

## Demo

Use labeled synthetic data without enabling live collection:

```bash
python3 scripts/signal_agent.py demo --reset
python3 scripts/signal_agent.py serve
```

## Resources

- `scripts/signal_agent.py`: CLI and local server entrypoint.
- `assets/company-profile.example.json`: editable onboarding profile.
- `assets/company-profile.schema.json`: profile schema.
- `references/agent-contract.md`: required agent input and output.
- `references/governance.md`: review and safety rules.
- `references/experiments.md`: assignment and learning rules.
- `references/providers.md`: connector contract.
