# REPO-STANDARDS.md

Standards for every public skill repository under github.com/jackterror. Reference implementation: social-demand-signal-agent.

## 1. Required files

Every repo ships with: SKILL.md (entrypoint), README.md, LICENSE (MIT, Jack Dalrymple), .gitignore, CREATOR.md, SOURCES.md, CHANGELOG.md, PACKAGE-DESCRIPTION.md, TEST-PROMPTS.md. Optional: examples/, reference/, MEGA-SKILL.md.

## 2. Standard .gitignore

Use the standard set (FILE C in the source prompt / see any compliant repo).

## 3. README template – section order

1. H1 in Title Case (never the repo slug)
2. One-liner: "A modular AI-ready [X] that [does Y], grounded in [Z]." – must match the GitHub repo description verbatim
3. What it does
4. Default behavior
5. Package structure – tree-format code block, not a bullet list
6. Agent Skill installation – standard block with Claude Code and Codex symlink commands plus an example invocation, referencing https://agentskills.io/specification
7. Notes (optional)
8. Creator and license – always the closing section, always: "Created by [Jack Dalrymple](https://www.jackdalrymple.com/), Founder of [Cap & Cut](https://capandcut.com/). See [CREATOR.md](CREATOR.md). Released under the MIT License. See [LICENSE](LICENSE)."

## 4. Brand domains – non-negotiable

jackdalrymple.com (the person – About panel website + Creator link) and capandcut.com (the studio – Creator block + CREATOR.md). Every repo links both, in the README closer and CREATOR.md. Missing either = checklist fail.

## 5. GitHub About panel

Description = README one-liner. Website = https://www.jackdalrymple.com/. Topics: 8–10, always including claude-skills, agent-skills, ai-agents, prompt-engineering, plus domain tags. Upload a social preview image.

## 6. Style rules

Spaced en dashes ( – ), never em dashes. No internal build notes in public docs. CHANGELOG dated, newest first.

## 7. Pre-publish checklist

- [ ] LICENSE present (MIT)
- [ ] README follows template order, Title Case H1
- [ ] Creator and license block closes the README
- [ ] Install block present with correct slug
- [ ] Tree-format structure block
- [ ] .gitignore matches standard set
- [ ] Repo description = README one-liner
- [ ] Website set to jackdalrymple.com
- [ ] Both brand domains linked in README closer and CREATOR.md
- [ ] 8–10 topics applied
- [ ] Social preview uploaded
- [ ] No packaging/internal notes in public docs
