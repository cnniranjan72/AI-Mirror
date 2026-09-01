"""Import behaviour from official platform data exports.

Why this exists: the Chrome extension reads a DOM that Instagram controls and
can change without notice, and it only ever sees what the user happens to
scroll past while it is installed. An official export is the opposite on both
counts — it is a stable, documented format, and it contains the account's
whole history in one file. It is also the only collection route that does not
depend on scraping a logged-in session.

Supported today:
  - Instagram "Download your information" (JSON): videos watched, posts seen,
    liked posts, saved posts.
  - Google Takeout, YouTube watch history (JSON).
  - Ad-targeting interests from either, imported as PROFILE CLAIMS rather than
    as behaviour — see _parse_profile_claims.

Design notes:

* TOLERANT BY DEFAULT. These formats are undocumented in practice and differ
  between export vintages and locales. Every parser is keyed off the SHAPE of
  the data rather than an exact filename, and anything unrecognised is skipped
  and counted rather than raising — a single odd record must never cost the
  user the other 40,000.
* Output is EventItem-shaped dicts, so imported events go through exactly the
  same /ingest pipeline as extension events. No second ingestion path exists
  to drift out of sync with the first.
* No network, no LLM. Parsing is pure and deterministic.
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Guard rails. A data export is user-supplied and arrives over the network, so
# every limit here exists to keep one upload from exhausting the process.
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024          # 200MB compressed
MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024    # 1GB total, guards zip bombs
MAX_MEMBER_BYTES = 64 * 1024 * 1024            # 64MB per JSON file
MAX_EVENTS = 50_000                            # per import


class ArchiveImportError(Exception):
    """Raised only for problems with the archive as a whole — an unreadable
    ZIP, or one large enough to be a denial-of-service attempt. Individual bad
    records never raise."""


# --------------------------------------------------------------------------
# timestamp handling
# --------------------------------------------------------------------------

def _from_epoch(value: Any) -> Optional[datetime]:
    """Instagram exports epoch SECONDS. Values are sanity-checked because a
    malformed record with a huge integer would otherwise produce a timestamp
    thousands of years out and skew every temporal statistic downstream."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    # 1990-01-01 .. 2100-01-01
    if not (631_152_000 <= seconds <= 4_102_444_800):
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _from_iso(value: Any) -> Optional[datetime]:
    """Google Takeout writes RFC3339 with a 'Z' suffix and often microseconds."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# --------------------------------------------------------------------------
# Instagram
# --------------------------------------------------------------------------

def _ig_string_map(record: Dict[str, Any]) -> Dict[str, Any]:
    """Instagram wraps most fields in {"string_map_data": {"Author": {"value": ...}}}.

    Locale matters here: the KEYS are translated in non-English exports, so
    reading `["Author"]` directly would silently yield nothing for a large
    share of users. Callers match on value shape instead.
    """
    raw = record.get("string_map_data")
    return raw if isinstance(raw, dict) else {}


def _ig_pick(string_map: Dict[str, Any], *candidates: str) -> Optional[str]:
    for key in candidates:
        entry = string_map.get(key)
        if isinstance(entry, dict) and entry.get("value"):
            return str(entry["value"])
    return None


def _ig_timestamp(record: Dict[str, Any], string_map: Dict[str, Any]) -> Optional[datetime]:
    for key, entry in string_map.items():
        if isinstance(entry, dict) and "timestamp" in entry:
            found = _from_epoch(entry["timestamp"])
            if found:
                return found
    for key in ("timestamp", "creation_timestamp", "taken_at"):
        if key in record:
            found = _from_epoch(record[key])
            if found:
                return found
    return None


def _parse_instagram_impressions(payload: Dict[str, Any], kind: str) -> List[Dict[str, Any]]:
    """videos_watched / posts_viewed: a viewing signal with an author and time."""
    events: List[Dict[str, Any]] = []
    for _key, records in payload.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            string_map = _ig_string_map(record)
            author = _ig_pick(string_map, "Author", "Username", "Name") or record.get("title") or "unknown"
            when = _ig_timestamp(record, string_map)
            if not when:
                continue
            events.append({
                "reel_id": f"ig_{kind}_{int(when.timestamp())}_{abs(hash(author)) % 100000}",
                "username": str(author),
                "caption": "",
                "hashtags": [],
                # An export records THAT something was watched, never for how
                # long. Emitting a fabricated duration would corrupt the watch
                # statistics the identity is built from, so this stays 0 and
                # the event contributes frequency only.
                "watch_time": 0.0,
                "timestamp": when.isoformat(),
                "platform": "instagram",
                "session_id": f"import_{when.date().isoformat()}",
                "source_url": "",
            })
    return events


def _parse_instagram_engagement(payload: Dict[str, Any], flag: str) -> List[Dict[str, Any]]:
    """likes / saves: {"likes_media_likes": [{"title": author,
    "string_list_data": [{"href":…, "timestamp": …}]}]}"""
    events: List[Dict[str, Any]] = []
    for _key, records in payload.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            author = record.get("title") or "unknown"
            entries = record.get("string_list_data")
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                when = _from_epoch(entry.get("timestamp"))
                if not when:
                    continue
                href = entry.get("href") or ""
                events.append({
                    "reel_id": f"ig_{flag}_{int(when.timestamp())}_{abs(hash(href or author)) % 100000}",
                    "username": str(author),
                    "caption": "",
                    "hashtags": [],
                    "watch_time": 0.0,
                    # The whole point of these files: an explicit, deliberate
                    # engagement signal, which a viewing record is not.
                    "liked": flag == "liked",
                    "saved": flag == "saved",
                    "timestamp": when.isoformat(),
                    "platform": "instagram",
                    "session_id": f"import_{when.date().isoformat()}",
                    "source_url": href,
                })
    return events


# --------------------------------------------------------------------------
# YouTube (Google Takeout)
# --------------------------------------------------------------------------

def _parse_youtube_watch_history(records: List[Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        # Takeout mixes YouTube and YouTube Music, and includes search activity
        # in the same file shape. Only watch events are behaviour.
        title = record.get("title") or ""
        if not title.lower().startswith("watched"):
            continue

        when = _from_iso(record.get("time"))
        if not when:
            continue

        channel = "unknown"
        subtitles = record.get("subtitles")
        if isinstance(subtitles, list) and subtitles and isinstance(subtitles[0], dict):
            channel = subtitles[0].get("name") or "unknown"

        url = record.get("titleUrl") or ""
        # "Watched <video title>" — the rest is the only free text an export
        # gives us, and it is what topic extraction has to work from.
        caption = title[len("Watched"):].strip() if len(title) > 7 else ""

        events.append({
            "reel_id": f"yt_{int(when.timestamp())}_{abs(hash(url or caption)) % 100000}",
            "username": str(channel),
            "caption": caption,
            "hashtags": [],
            "watch_time": 0.0,
            "timestamp": when.isoformat(),
            "platform": "youtube",
            "surface": "watch",
            "session_id": f"import_{when.date().isoformat()}",
            "source_url": url,
        })
    return events


# --------------------------------------------------------------------------
# platform profile claims (ad-targeting interests)
# --------------------------------------------------------------------------
#
# These are NOT behaviour. They are what the platform asserts about the person,
# lifted verbatim from their own export, so that the twin's evidence-based
# model can be checked against them. Everyone can already SEE this list in
# their settings; what nobody can do is test whether it is true.

# Key names that indicate a payload is a list of inferred interests. Matched
# loosely because Meta has shipped at least three spellings of this file across
# export vintages ("topics_your_interested_in", "inferred_topics", ...).
_CLAIM_KEY_HINTS = ("interest", "topic", "ad_preference", "ads_interest")

# Value fields inside the usual string_map_data wrapper.
_CLAIM_VALUE_KEYS = ("Interest", "Name", "Topic", "Value", "Title")


def _looks_like_claims_payload(name: str, payload: Any) -> bool:
    lowered = name.lower()
    if "ads_interest" in lowered or "ad_preferences" in lowered or "your_topics" in lowered:
        return True
    if not isinstance(payload, dict):
        return False
    return any(hint in key.lower() for key in payload.keys() for hint in _CLAIM_KEY_HINTS)


def normalize_claim_label(raw: str) -> str:
    """Casefold and collapse whitespace/punctuation so "Robotics " and
    "robotics" are one claim. Deliberately conservative — it must not conflate
    genuinely different claims, because a false merge here would silently make
    a platform's assertion disappear from the audit."""
    if not raw:
        return ""
    cleaned = " ".join(str(raw).split()).strip().strip(".,;:").lower()
    return cleaned


def _extract_claim_strings(payload: Any) -> List[str]:
    """Pull interest labels out of whichever shape this export vintage used."""
    found: List[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        # Bounded: an export is user-supplied, and a pathological nesting depth
        # should not be able to blow the stack.
        if depth > 6:
            return
        if isinstance(node, str):
            if 1 < len(node) <= 120:
                found.append(node)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
            return
        if isinstance(node, dict):
            string_map = node.get("string_map_data")
            if isinstance(string_map, dict):
                value = _ig_pick(string_map, *_CLAIM_VALUE_KEYS)
                if value:
                    found.append(value)
                return
            # Newer exports drop the wrapper and use a flat {"name": ...}.
            for key in ("name", "title", "interest", "topic", "value"):
                if isinstance(node.get(key), str):
                    found.append(node[key])
                    return
            for item in node.values():
                walk(item, depth + 1)

    walk(payload)
    return found


def _parse_profile_claims(name: str, payload: Any, platform: str) -> List[Dict[str, Any]]:
    claims = []
    seen = set()
    for raw in _extract_claim_strings(payload):
        label = normalize_claim_label(raw)
        # Single characters and pure numbers are export scaffolding, not claims.
        if len(label) < 2 or not any(ch.isalpha() for ch in label) or label in seen:
            continue
        seen.add(label)
        claims.append({
            "platform": platform,
            "claim_type": "ad_interest",
            "label": label,
            # Kept verbatim so the audit can quote the export rather than a
            # normalised paraphrase of it.
            "raw_label": str(raw).strip(),
            "source_file": name,
        })
    return claims


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------

def _classify_and_parse(name: str, payload: Any) -> Tuple[str, List[Dict[str, Any]]]:
    """Route one parsed JSON document to a parser.

    Matches on filename hints first, then on shape, because export layouts move
    between vintages while the payload shape is stable.
    """
    lowered = name.lower()

    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and (
            "titleUrl" in payload[0] or "subtitles" in payload[0] or "header" in payload[0]
        ):
            return "youtube_watch_history", _parse_youtube_watch_history(payload)
        return "unknown", []

    if not isinstance(payload, dict):
        return "unknown", []

    keys = " ".join(payload.keys()).lower()

    if "videos_watched" in lowered or "videos_watched" in keys:
        return "instagram_videos_watched", _parse_instagram_impressions(payload, "watched")
    if "posts_viewed" in lowered or "posts_viewed" in keys:
        return "instagram_posts_viewed", _parse_instagram_impressions(payload, "viewed")
    if "liked" in lowered or "media_likes" in keys:
        return "instagram_likes", _parse_instagram_engagement(payload, "liked")
    if "saved" in lowered or "saved_media" in keys:
        return "instagram_saves", _parse_instagram_engagement(payload, "saved")

    return "unknown", []


def _iter_json_documents(data: bytes, filename: str) -> Iterable[Tuple[str, Any]]:
    """Yield (member_name, parsed_json) from a ZIP or a bare JSON file."""
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            total = sum(info.file_size for info in archive.infolist())
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ArchiveImportError(
                    f"Archive expands to {total // (1024*1024)}MB, over the "
                    f"{MAX_UNCOMPRESSED_BYTES // (1024*1024)}MB limit"
                )
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                if info.file_size > MAX_MEMBER_BYTES:
                    logger.warning("Skipping oversized archive member %s", info.filename)
                    continue
                try:
                    with archive.open(info) as handle:
                        yield info.filename, json.loads(handle.read().decode("utf-8", "replace"))
                except Exception as e:
                    # One unreadable file must not abort an otherwise good import.
                    logger.warning("Skipping unreadable member %s: %s", info.filename, e)
        return

    try:
        yield filename, json.loads(data.decode("utf-8", "replace"))
    except Exception as e:
        raise ArchiveImportError(f"File is neither a ZIP archive nor valid JSON: {e}") from e


def parse_archive(data: bytes, filename: str = "export.zip") -> Dict[str, Any]:
    """Parse an export into EventItem-shaped dicts.

    Returns {"events": [...], "profile_claims": [...], "sources": {parser:
    count}, "skipped_files": n, "truncated": bool}. `sources` is surfaced to
    the user so an import that found nothing can say WHICH files it looked at
    rather than failing mutely.

    `profile_claims` are what the PLATFORM asserts about the user (its
    ad-targeting interests), kept strictly separate from `events`, which are
    what the user actually did. The separation is the point: the twin is built
    only from events, so it remains an independent model capable of testing
    the claims.
    """
    if not data:
        raise ArchiveImportError("Empty file")
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ArchiveImportError(
            f"File is {len(data) // (1024*1024)}MB, over the "
            f"{MAX_ARCHIVE_BYTES // (1024*1024)}MB limit"
        )

    events: List[Dict[str, Any]] = []
    claims: List[Dict[str, Any]] = []
    sources: Dict[str, int] = {}
    skipped = 0
    truncated = False

    for member_name, payload in _iter_json_documents(data, filename):
        # Checked BEFORE the event parsers: an ad-interests file is a set of
        # assertions about the person, not a record of anything they did, and
        # must never be able to enter the pipeline as behaviour.
        if _looks_like_claims_payload(member_name, payload):
            platform = "google" if "takeout" in member_name.lower() or "google" in member_name.lower() else "meta"
            found = _parse_profile_claims(member_name, payload, platform)
            if found:
                claims.extend(found)
                sources[f"{platform}_ad_interests"] = sources.get(f"{platform}_ad_interests", 0) + len(found)
                continue

        kind, parsed = _classify_and_parse(member_name, payload)
        if not parsed:
            if kind == "unknown":
                skipped += 1
            continue

        remaining = MAX_EVENTS - len(events)
        if remaining <= 0:
            truncated = True
            break
        if len(parsed) > remaining:
            parsed = parsed[:remaining]
            truncated = True

        sources[kind] = sources.get(kind, 0) + len(parsed)
        events.extend(parsed)

    # Exports overlap: a liked post also appears in posts_viewed, and re-exports
    # repeat history wholesale. Deduplicating here keeps a user who imports the
    # same archive twice from doubling their own history.
    seen = set()
    deduped = []
    for event in events:
        key = (event["platform"], event["reel_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)

    # Oldest first, so the pipeline sees the account's history in the order it
    # happened — identity evolution is a sequence, not a set.
    deduped.sort(key=lambda e: e.get("timestamp") or "")

    # Same claim can appear in several export files; identity is
    # (platform, label).
    seen_claims = set()
    deduped_claims = []
    for claim in claims:
        key = (claim["platform"], claim["label"])
        if key in seen_claims:
            continue
        seen_claims.add(key)
        deduped_claims.append(claim)

    return {
        "events": deduped,
        "profile_claims": deduped_claims,
        "sources": sources,
        "skipped_files": skipped,
        "truncated": truncated,
        "duplicates_removed": len(events) - len(deduped),
    }
