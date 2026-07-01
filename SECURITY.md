# Security Policy

## Reporting a vulnerability

Do not open a public issue for a security vulnerability or exposed credential.

Email `jack@capandcut.com` with:

- the affected file, command, or endpoint
- steps to reproduce the issue
- the likely impact
- any suggested mitigation

Do not include live customer data, API keys, or access tokens in the report.

## Supported version

Security fixes target the latest release on the default branch.

## Operating boundaries

The local server is designed for one trusted user and binds to `127.0.0.1`. The project does not provide authentication, multi-user authorization, autonomous posting, or a production-hosted control plane.

Keep `.env`, `runtime/`, local databases, generated runs, and provider credentials out of version control.
