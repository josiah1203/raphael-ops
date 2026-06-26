# raphael-ops

Observability, reliability, release operations

## API

- Prefix: `/v1/ops`
- Port: `8103`
- Health: `GET /health`

## Events

_Published and consumed events documented in `openapi.yaml` and raphael-contracts._

## Development

```bash
uv sync
uv run uvicorn raphael_ops.app:app --reload --port 8103
```

Part of the [Raphael Platform](https://github.com/hummingbird-labs) by HummingBird Labs.
