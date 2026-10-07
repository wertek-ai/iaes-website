# iaes.dev

> Website for the Industrial Asset Event Standard.

**Live:** [https://iaes.dev](https://iaes.dev)

## Overview

Static single-page site that documents the IAES specification, event types, wire format, SDKs, and integrations. Supports 14 languages.

## Structure

```
├── index.html          # Main page (spec overview, install, examples, i18n)
├── js/
│   └── i18n.js         # Translation strings for 14 languages
├── schemas/            # JSON Schema files (linked from spec section)
├── examples/           # JSON examples (linked from event type cards)
└── spec/               # Rendered specification pages
```

## Languages

AR, DE, EN, ES, FR, HI, IT, JA, KO, PL, PT, RU, TR, ZH

Language switching is client-side via `i18n.js`. The `data-i18n` attribute on HTML elements maps to translation keys.

## Deployment

- **Platform:** Netlify
- **Repo:** [`wertek-ai/iaes-website`](https://github.com/wertek-ai/iaes-website)
- **Branch:** `main`
- **Build:** Static site (no build step)
- **Publish directory:** root (`/`)
- **Domain:** iaes.dev (Netlify DNS)

Pushes to `main` trigger automatic deployment.

## SDKs Documented

The packages follow the specification's major and minor: a `2.x.y` package implements
IAES `2.x`. The registries are the authority for what is published; the table states
the line, not a release.

| SDK | Package | Line |
|-----|---------|------|
| Python | [`iaes`](https://pypi.org/project/iaes/) | 2.x |
| TypeScript | [`@iaes/sdk`](https://www.npmjs.com/package/@iaes/sdk) | 2.x |
| Node-RED | [`node-red-contrib-iaes`](https://flows.nodered.org/node/node-red-contrib-iaes) | 2.x |
| n8n | [`n8n-nodes-iaes`](https://www.npmjs.com/package/n8n-nodes-iaes) | 2.x |

As of 2026-10-07 the registries serve `2.0.2` of all four; producing `asset.state`
(IAES 2.1) needs the `2.1.x` packages once they are published.

## Related Repos

| Repo | Purpose |
|------|---------|
| [`wertek-ai/iaes`](https://github.com/wertek-ai/iaes) | Spec, schemas, SDKs (Python + TypeScript + Node-RED) |
| [`wertek-ai/iaes-website`](https://github.com/wertek-ai/iaes-website) | This website |

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
