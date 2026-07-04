# GitHub Publishing Checklist

## Repository metadata

- Name: `social-demand-signal-agent`
- About: An agentic social listening system that finds customer pain and buying intent, drafts human-reviewed A/B responses, and learns from tracked outcomes.
- Topics: `social-listening`, `agent-skills`, `ai-agents`, `growth-marketing`, `demand-generation`, `human-in-the-loop`, `ab-testing`, `customer-intelligence`, `social-media-monitoring`, `local-first`, `python`
- License: MIT
- Release title: `Social Demand Signal Agent v0.1.0`

## Before publishing

- [x] Create the public repository with fresh history and preserve launcher permissions.
- [x] Push `main` after Jack's approval.
- [x] Confirm the initial GitHub Actions CI run is green.
- [x] Run the local unit, integration, clean-install, browser, archive, link, secret, and provenance checks.
- [x] Run Agent Skills validation.
- [x] Complete the clean-install and archive audits.
- [x] Confirm release screenshots contain fixture data and no credentials.
- [x] Run `npm install`, `npx playwright install chromium`, and `npm run capture`.
- [x] Inspect all three release images and add the two screenshots to README.
- [ ] Run the isolated with-skill versus baseline functional evals.
- [ ] Run one authenticated SocialCrawl connection and current-source contract check.
- [x] Confirm the Git author and commit messages.
- [x] Review README links and commands from the source archive.
- [ ] Add the repository website, topics, and social preview.
- [ ] Confirm CI is green on the final release commit.
- [x] Obtain Jack's approval to create the release.
- [ ] Publish and verify the `v0.1.0` release and both downloads.

## Release files

- `social-demand-signal-agent.skill`
- `social-demand-signal-agent-v0.1.0.zip`
