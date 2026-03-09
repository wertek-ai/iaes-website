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

| SDK | Package | Version |
|-----|---------|---------|
| Python | [`iaes`](https://pypi.org/project/iaes/) | 0.2.0 |
| TypeScript | [`@iaes/sdk`](https://www.npmjs.com/package/@iaes/sdk) | 0.2.0 |
| Node-RED | [`node-red-contrib-iaes`](https://flows.nodered.org/node/node-red-contrib-iaes) | 0.3.0 |

## Related Repos

| Repo | Purpose |
|------|---------|
| [`wertek-ai/iaes`](https://github.com/wertek-ai/iaes) | Spec, schemas, SDKs (Python + TypeScript + Node-RED) |
| [`wertek-ai/iaes-website`](https://github.com/wertek-ai/iaes-website) | This website |

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
