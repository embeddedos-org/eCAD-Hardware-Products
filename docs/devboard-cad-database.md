# Development-Board CAD Database (issue #28)

A board-by-board master database of third-party development-board CAD
availability. Every record binds one exact board and hardware revision;
family-level claims are not permitted (see issue #28, sections 9–12).

## Source hierarchy

Per issue #28, section 10, preferred source order is:

1. Manufacturer's official CAD/design-file repository
2. Manufacturer's official product page
3. Manufacturer's official GitHub repository
4. Manufacturer's official documentation
5. Authorized distributor documentation
6. Community repositories only when no official source exists

## Record lifecycle

- `incomplete`: identity recorded; availability and licensing unverified.
- `partial`: some formats verified against official sources.
- `verified`: identity, revision, all claimed formats, and licensing verified
  against official sources for the stated revision.

Availability is tri-state per format: `true` (verified present), `false`
(verified absent), `null` (unknown). A positive query matches only `true`.

## Schema

`schemas/devboard-cad/v1/board-record.schema.json`

## Query

```bash
python3 tools/devboard_cad/query.py list
python3 tools/devboard_cad/query.py with-formats step
python3 tools/devboard_cad/query.py full-stack
python3 tools/devboard_cad/query.py commercial-reuse
python3 tools/devboard_cad/query.py mechanical
python3 tools/devboard_cad/query.py open-electrical
```

The six queries above correspond to the six example queries in issue #28,
section 11.
