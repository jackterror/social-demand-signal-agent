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

The local server is designed for one trusted user and accepts loopback addresses only. State-changing browser requests require a same-origin custom header. Responses disable caching and apply a restrictive content security policy.

Provider credentials are stored only in `.env`. Process environment values take precedence. The dashboard returns credential status but never the credential value. Profile export, SQLite state, logs, screenshots, and release archives must remain credential-free.

The project does not provide authentication, multi-user authorization, autonomous posting, or a production-hosted control plane.

Keep `.env`, `runtime/`, local databases, generated runs, and provider credentials out of version control.
