# ChatOps Incident Update Runbook

## Goal

Convert technical incident analysis into a concise update for engineering, support, and stakeholders.

## Good Incident Update Structure

- Status
- Impact
- Root cause or suspected cause
- Evidence
- Current mitigation
- Next actions
- Owner
- Next update time

## Tone

- Be clear and calm.
- Avoid unnecessary technical noise.
- Do not overstate certainty.
- Separate confirmed facts from assumptions.
- Include what changed, what is being done, and what happens next.

## Example

Status: Investigating

Impact:
Checkout requests are slow for some users.

Current Finding:
Payment-service latency appears elevated and checkout-service is timing out on payment calls.

Evidence:
- checkout-service logs show timeout calling payment-service.
- payment-service metrics show elevated p95 latency.

Actions:
- Investigating payment-service database connection pool.
- Monitoring checkout latency and error rate.

Owner:
SRE / Platform team

Next Update:
In 30 minutes or sooner if status changes.
