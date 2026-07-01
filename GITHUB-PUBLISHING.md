# GitHub Publishing Checklist

## Repository metadata

- Name: `social-demand-signal-agent`
- About: An agentic social listening system that finds customer pain and buying intent, drafts human-reviewed A/B responses, and learns from tracked outcomes.
- Topics: `social-listening`, `agent-skills`, `ai-agents`, `growth-marketing`, `demand-generation`, `human-in-the-loop`, `ab-testing`, `customer-intelligence`, `social-media-monitoring`, `local-first`, `python`
- License: MIT
- Release title: `Social Demand Signal Agent v0.1.0`

## Before publishing

- [ ] Run the full test suite without skipped server tests.
- [ ] Run Agent Skills validation.
- [ ] Complete the clean-install and archive audits.
- [ ] Confirm release screenshots contain fixture data and no credentials.
- [ ] Run `npm install`, `npx playwright install chromium`, and `npm run capture`.
- [ ] Inspect all three release images and add the two screenshots to README.
- [ ] Run one authenticated SocialCrawl connection and current-source contract check.
- [ ] Confirm the Git author and commit message.
- [ ] Review README links and commands from the source archive.
- [ ] Create the repository only after Jack approves.
- [ ] Push `main` only after Jack approves.
- [ ] Create the release only after Jack approves.

## Release files

- `social-demand-signal-agent.skill`
- `social-demand-signal-agent-v0.1.0.zip`
