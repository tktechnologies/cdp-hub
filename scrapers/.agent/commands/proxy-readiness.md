# Command: Proxy Readiness Check

Validate an ISP/static residential proxy before using it with live supplier
scrapes.

**Full IPRoyal guide:** [docs/runbooks/iproyal-isp-proxy-setup.md](../../docs/runbooks/iproyal-isp-proxy-setup.md)

## Command

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/proxy_readiness_check.py \
  --proxy-url 'http://user:pass@host:12323'
```

Use `--from-env` after setting `PROXY_ROTATION_ENABLED=true` and `PROXY_URLS`.

## Acceptance

- Playwright check passes for every configured proxy.
- Egress IP matches the purchased proxy details.
- Credentials are masked in output and are not committed.
- Supplier smoke tests: `uv run python scripts/proxy_site_smoke.py --from-env`
  (see [.agent/workflows/proxy-rollout.md](../workflows/proxy-rollout.md)).
