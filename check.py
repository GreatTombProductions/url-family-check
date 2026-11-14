#!/usr/bin/env python3
"""Ask each address once, with no credentials, and do not follow redirects.

A redirect is recorded and stopped. On these hosts the login is often that
redirect, so following it would hide the gate. A 200 means this address
returned a page; the body is not read and is not judged.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_URLS = 40
TIMEOUT = 20
USER_AGENT = "url-family-check"


class _ReturnAnyStatus(urllib.request.HTTPErrorProcessor):
    """Leave 3xx/4xx/5xx as responses. Never turn them into exceptions."""

    def http_response(self, request, response):
        return response

    https_response = http_response


def _opener():
    # No RedirectHandler: a 302 stays a 302.
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPSHandler())
    opener.add_handler(_ReturnAnyStatus())
    return opener


def normalize(raw):
    text = (raw or "").strip()
    if not text or len(text) > 2000:
        raise ValueError("address is empty or longer than 2000 characters")
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https"):
        raise ValueError("only http and https addresses")
    if parts.username is not None or parts.password is not None:
        raise ValueError("an address with a username or password is refused")
    if not parts.hostname:
        raise ValueError("address has no host")
    path = parts.path or "/"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def verdict(status):
    if status in (301, 302, 303, 307, 308):
        return "redirect"
    if status == 401:
        return "challenged"
    if status == 403:
        return "refused"
    if 200 <= status <= 299:
        return "served"
    return "other"


def probe(url, opener=None, timeout=TIMEOUT):
    """One request. Returns a dict. Does not follow redirects or send cookies."""
    target = normalize(url)
    request = urllib.request.Request(
        target,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        method="GET",
    )
    row = {"url": target, "status": None, "verdict": "other", "location": "", "error": ""}
    try:
        response = (opener or _opener()).open(request, timeout=timeout)
        try:
            row["status"] = response.status
            row["verdict"] = verdict(response.status)
            row["location"] = response.headers.get("Location") or ""
        finally:
            response.close()
    except Exception as exc:  # DNS, timeout, TLS: a failed ask, not a page.
        row["error"] = type(exc).__name__
    return row


def format_row(row):
    status = "" if row["status"] is None else str(row["status"])
    bits = [row["url"], status, row["verdict"]]
    if row["location"]:
        bits.append(row["location"])
    if row["error"]:
        bits.append(row["error"])
    return "\t".join(bits)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ask each address once, without credentials, and do not follow redirects."
    )
    parser.add_argument("urls", nargs="*", help="addresses to ask (40 at most)")
    parser.add_argument("--file", help="text file with one address per line")
    args = parser.parse_args(argv)
    raw = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            raw.extend(line.strip() for line in handle if line.strip() and not line.startswith("#"))
    if not raw:
        parser.error("give at least one address")
    if len(raw) > MAX_URLS:
        parser.error(f"at most {MAX_URLS} addresses")
    print("url\tstatus\tverdict\tlocation_or_error")
    print("# A redirect is not followed. It may be the login. served means HTTP 200-class, body not read.")
    failed = 0
    opener = _opener()
    for item in raw:
        try:
            row = probe(item, opener=opener)
        except ValueError as exc:
            row = {"url": item.strip(), "status": None, "verdict": "other", "location": "", "error": str(exc)}
        if row["error"] or row["status"] is None:
            failed += 1
        print(format_row(row))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
