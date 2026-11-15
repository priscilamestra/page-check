"""Read-only, fail-closed deployment preflight. Does not deploy anything."""
from __future__ import annotations

import argparse
import json

from pagecheck.common.security.vercel_readiness import vercel_readiness


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether Page Check is ready for Vercel")
    parser.add_argument("--strict", action="store_true", help="Exit 2 if any deployment gate is open")
    args = parser.parse_args()
    report = vercel_readiness()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and not report["deploy_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
