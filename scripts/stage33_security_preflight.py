"""Offline, no-secret check of STAGE33 source and deployment defaults."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'src/pagecheck/common/security/admission.py',
    'src/pagecheck/common/security/deployment.py',
    'src/pagecheck/api/routes/audit.py',
    'src/pagecheck/ui/app.py',
    'src/pagecheck/acquisition/browser/public_navigation.py',
    'render.yaml',
    'deploy/Dockerfile.api',
    'tests/unit/test_stage33_public_audit_security.py',
)


def main() -> None:
    missing = [file for file in FILES if not (ROOT / file).is_file()]
    if missing:
        raise SystemExit('STAGE33 files missing: ' + ', '.join(missing))
    blueprint = (ROOT / 'render.yaml').read_text(encoding='utf-8')
    for flag in ('PAGECHECK_PUBLIC_AUDITS_ENABLED', 'PAGECHECK_EGRESS_ISOLATED',
                 'PAGECHECK_ALLOW_LIVE_FETCH', 'PAGECHECK_ALLOW_LIVE_BROWSER'):
        if f'{flag}\n        value: "0"' not in blueprint:
            raise SystemExit(f'Fail-closed production configuration missing for {flag}')
    if 'type: pserv' not in blueprint or '"--workers", "1"' not in (ROOT / 'deploy/Dockerfile.api').read_text(encoding='utf-8'):
        raise SystemExit('Private single-worker API deployment expected.')
    print('STAGE33 private API authentication and admission files: PRESENT')
    print('Render public audit flags: DISABLED by default')
    print('Network egress isolation: NOT VERIFIED - manual infrastructure review required')
    print('Docker builds / Chromium / real production audit: NOT VERIFIED')
    print('No network access, credentials, deployment or push performed.')


if __name__ == '__main__':
    main()
