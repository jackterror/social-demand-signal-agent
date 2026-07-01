# Contributing

Contributions are welcome when they preserve the project's core boundaries: company-owned configuration, human-reviewed responses, deterministic experiment assignment, and learning from observed outcomes.

## Before opening a pull request

1. Create a focused branch.
2. Keep fixtures synthetic and free of personal data, customer data, and credentials.
3. Add or update tests for changed behavior.
4. Run the full checks:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_audit.py .
python3 scripts/package_release.py
```

5. Explain the user problem, the change, and any safety or data implications in the pull request.

## Contribution priorities

- provider adapters with tested source URLs and timestamps
- stronger signal relevance and routing
- clearer reviewer workflows
- first-party outcome integrations
- experiment analysis that preserves message-family and platform context
- accessibility, browser coverage, and documentation
- onboarding, migration, and credential-redaction coverage

## Boundaries

Pull requests should not add:

- autonomous posting or direct messages
- concealed affiliation
- learning from fixture or fabricated outcomes
- collection of private or access-controlled data
- hard-coded company assumptions
- untested claims of platform support

By contributing, you agree that your contribution will be licensed under the MIT License.
