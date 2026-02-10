#!/usr/bin/env python3
"""
VisibleAI GEO Audit — Check brand visibility across AI search engines.

Usage:
    python3 audit.py "Brand Name" --website "https://example.com" --industry "SaaS"
    python3 audit.py "Shopify" --industry "E-commerce"
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

API_URL = "https://visibleai.space/api/v1/audit"


def run_audit(brand: str, website: str = "", industry: str = "general", competitors: list = None):
    payload = {
        "brand": brand,
        "industry": industry,
    }
    if website:
        payload["website"] = website
    if competitors:
        payload["competitors"] = competitors

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def print_report(result: dict):
    print(f"\n{'='*50}")
    print(f"  GEO AUDIT: {result['brand']}")
    print(f"  Industry: {result['industry']}")
    if result.get('website'):
        print(f"  Website: {result['website']}")
    print(f"{'='*50}")
    print(f"\n  OVERALL SCORE: {result['overall_score']}/100 — Grade {result['grade']}\n")

    if result.get('engines'):
        print("  ENGINE SCORES:")
        for engine, data in result['engines'].items():
            print(f"    {engine.upper():12s} {data['score']:3d}/100  ({data['mentions']} mentions, {data['sentiment']})")

    if result.get('categories'):
        print("\n  CATEGORIES:")
        for cat, data in result['categories'].items():
            print(f"    {cat.capitalize():12s} {data['score']:3d}/100  — {data['detail']}")

    if result.get('site_analysis'):
        sa = result['site_analysis']
        print(f"\n  SITE ANALYSIS:")
        print(f"    Schema markup:    {'✓ Found' if sa.get('schema_markup') else '✗ Missing'}")
        print(f"    Meta description: {'✓ Found' if sa.get('meta_description') else '✗ Missing'}")

    if result.get('recommendations'):
        print(f"\n  RECOMMENDATIONS:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"    {i}. {rec}")

    print(f"\n{'='*50}")
    print(f"  Full report: https://visibleai.space")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="VisibleAI GEO Audit")
    parser.add_argument("brand", help="Brand name to audit")
    parser.add_argument("--website", "-w", default="", help="Website URL")
    parser.add_argument("--industry", "-i", default="general", help="Industry/vertical")
    parser.add_argument("--competitors", "-c", nargs="*", default=[], help="Competitor names")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = run_audit(args.brand, args.website, args.industry, args.competitors)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
