"""Read-only external source fetching with strict safety guards.

Every fetch is:
  - limited to http/https,
  - SSRF-guarded (resolved host IP must not be private/loopback/link-local/
    multicast/reserved),
  - size-capped and time-limited,
  - decoded to plain text (HTML is stripped to text),
  - a read-only GET with a descriptive user agent.

Platform fetches (website/facebook/instagram/twitter/linkedin/youtube) are all
best-effort public reads. YouTube can use the official Data API v3 when
YOUTUBE_API_KEY is configured; otherwise public page fetch is attempted.
"""

import html as html_lib
import ipaddress
import re
import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from ..config import settings

MAX_BYTES = 2_000_000
TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (NGO Report Studio research agent; "
    "read-only public fetch; contact: report@yourorg.example)"
)


class FetchError(RuntimeError):
    pass


def _is_safe_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag in ("p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _to_text(data: bytes, content_type: str) -> str:
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", content_type or "")
    if m:
        charset = m.group(1)
    try:
        text = data.decode(charset, errors="replace")
    except LookupError:
        text = data.decode("utf-8", errors="replace")

    if "html" in (content_type or "").lower() or "<" in text[:2000]:
        parser = _TextExtractor()
        parser.feed(text)
        text = "".join(parser.parts)
    text = html_lib.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[: MAX_BYTES]


def fetch_text(url: str) -> str:
    """Fetch a public URL and return its text. Raises FetchError on any issue."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("Only http/https URLs are allowed")
    host = parsed.hostname
    if not host or not _is_safe_host(host):
        raise FetchError("URL host is not publicly routable (SSRF guard)")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/plain,application/json,application/rss+xml,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES + 1)
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {host}") from exc
    except Exception as exc:
        raise FetchError(f"Fetch failed for {host}: {exc}") from exc

    if len(data) > MAX_BYTES:
        data = data[:MAX_BYTES]
    text = _to_text(data, content_type)
    if not text:
        raise FetchError(f"No readable content returned from {host}")
    return text


def _youtube_via_api(channel_handle: str) -> str:
    """Official YouTube Data API v3 (read-only, free tier)."""
    import json
    import urllib.parse

    key = settings.youtube_api_key
    handle = channel_handle.lstrip("@")
    base = "https://www.googleapis.com/youtube/v3"

    def _get(path, params):
        params = dict(params, key=key)
        url = f"{base}{path}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())

    channels = _get("/channels", {"part": "contentDetails,statistics,snippet", "forHandle": handle})
    items = channels.get("items") or []
    if not items:
        raise FetchError("YouTube channel not found")
    ch = items[0]
    stats = ch.get("statistics", {})
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    lines = [f"YouTube channel: {ch['snippet'].get('title')}",
             f"Subscribers: {stats.get('subscriberCount')}", f"Videos: {stats.get('videoCount')}",
             f"Views: {stats.get('viewCount')}", "Recent videos:"]
    try:
        pl = _get("/playlistItems", {"part": "snippet,contentDetails", "playlistId": uploads, "maxResults": 10})
        for item in pl.get("items", []):
            sn = item["snippet"]
            lines.append(f"- {sn['publishedAt'][:10]} | {sn['title']}")
    except Exception:
        pass
    return "\n".join(lines)


def fetch_platform(platform: str, url: str | None) -> str:
    """Fetch a source for a platform. Raises FetchError on failure."""
    if not url or not url.strip():
        raise FetchError("No URL provided")
    url = url.strip()

    if platform == "youtube" and settings.youtube_api_key:
        handle = url.rstrip("/").rsplit("/", 1)[-1]
        return _youtube_via_api(handle)

    return fetch_text(url)