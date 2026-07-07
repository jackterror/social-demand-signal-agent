# Test Prompts

Use these prompts to check whether the skill routes correctly and preserves its guardrails.

## Should trigger

- Set up social listening for people complaining that expense reports take all Friday, then draft two replies for review.
- Watch Reddit and X for people actively looking to replace their project-management tool.
- Build a human-reviewed reply queue from public product complaints.
- Find buying intent in these public posts and test an empathy-first reply against a utility-first one.
- Monitor competitor frustration and learn which response gets qualified demos.

## Should not trigger

- Write one launch announcement for LinkedIn.
- Schedule our approved posts for next week.
- Build an email lifecycle campaign for trial users.
- Scrape private profiles and send them unsolicited direct messages.
- Export our CRM contacts to a spreadsheet.

## Functional checks

- Configure a new company profile without storing credentials in the profile.
- Import `assets/fixtures/signals.json`, route each signal, and draft both variants for eligible records.
- Interpret experiment results without treating fixture events as observed outcomes.
