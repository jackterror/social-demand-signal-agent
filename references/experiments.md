# Experiment Rules

## Assignment

Assign a variant from a stable hash of signal ID and message family before generating drafts. Keep assignment deterministic when a signal is reprocessed.

Do not let a reviewer choose the experiment variant. The reviewer may edit, reject, or escalate the assigned response.

## Test design

- Compare variants within the same message family and platform.
- Change one meaningful variable at a time.
- Keep disclosure, approved claims, CTA, and safety boundaries stable.
- Record the hypothesis before exposure.

## Events

- `posted` is the exposure denominator.
- The configured primary event is the conversion numerator.
- The configured guardrail event measures downside.
- Record only observed or reviewer-entered events in real analysis.

## Interpretation

- `insufficient_data`: either arm is below the minimum sample.
- `directional`: minimum samples exist, but uncertainty remains.
- `validated`: Wilson intervals separate and the guardrail-rate difference stays within two percentage points.

Never call a directional leader a winner. Never generalize a result across message families or platforms without a new test.
