# ADR 0014: Strict Demo Identity and Production OIDC Boundary

Status: Accepted

Demo identity is allowed only outside production. Production must verify OIDC signatures, issuer, audience, expiry, and deployment policy before claims reach the adapter. Organization and permission checks remain mandatory after authentication.
