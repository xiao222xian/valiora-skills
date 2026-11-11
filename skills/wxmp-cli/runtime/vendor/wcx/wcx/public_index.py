"""Public article discovery for Official Accounts.

WeChat's authenticated cross-account article-list endpoints started returning
``ret=200013`` for first-page requests across multiple clients in late July
2026.  Public article pages still work, so external-account discovery uses the
public Sogou Weixin index and leaves the logged-in Official Account session out
of the article-list path.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from platformdirs import user_data_dir


SOGOU_BASE = "https://weixin.sogou.com"
SOGOU_SEARCH_URL = f"{SOGOU_BASE}/weixinwap"
DEFAULT_SEARCH_PAGES = 5
CACHE_TTL_SECONDS = 6 * 60 * 60
EMPTY_CACHE_TTL_SECONDS = 5 * 60
RENAMED_PUBLISHER_GROUP_LIMIT = 3
RENAMED_PUBLISHER_PROBE_TIMEOUT_SECONDS = 5
SIGNATURE_QUERY_LENGTH = 5
SIGNATURE_QUERY_LIMIT = 3
DEFAULT_CACHE_PATH = Path(user_data_dir("wcx")) / "public-index-cache.json"

PUBLIC_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _safe_hash(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def _debug(event: str, **fields: object) -> None:
    payload = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
        for key, value in fields.items()
    )
    suffix = f" {payload}" if payload else ""
    print(f"[DEBUG][wcx.public_index] {event}{suffix}", file=sys.stderr, flush=True)


class PublicIndexError(RuntimeError):
    """The public article index did not return a usable result."""


class PublicIndexEmpty(PublicIndexError):
    """The public index has no articles for the selected account yet."""


@dataclass(frozen=True)
class PublicArticleCandidate:
    stable_id: str
    title: str
    digest: str
    cover: str
    create_time: int
    redirect_url: str
    referer: str
    publisher: str = ""


@dataclass(frozen=True)
class PublicArticle:
    aid: str
    title: str
    link: str
    digest: str
    cover: str
    create_time: int


class SogouPublicIndex:
    """Discover and resolve public WeChat articles without backend cookies."""

    def __init__(
        self,
        *,
        session=None,
        sleeper: Callable[[float], None] = time.sleep,
        search_pages: int = DEFAULT_SEARCH_PAGES,
        min_delay: float = 0.35,
        max_delay: float = 0.75,
        resolve_min_delay: float = 0.12,
        resolve_max_delay: float = 0.28,
        cache_path: Path | None = DEFAULT_CACHE_PATH,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._session = session or cffi_requests.Session(headers=PUBLIC_HEADERS)
        self._sleeper = sleeper
        self._search_pages = max(1, min(int(search_pages), 10))
        self._min_delay = max(0.0, float(min_delay))
        self._max_delay = max(self._min_delay, float(max_delay))
        self._resolve_min_delay = max(0.0, float(resolve_min_delay))
        self._resolve_max_delay = max(
            self._resolve_min_delay,
            float(resolve_max_delay),
        )
        self._cache_path = cache_path
        self._clock = clock
        self._candidate_cache: dict[
            tuple[str, str, str], list[PublicArticleCandidate]
        ] = {}
        self._resolved_cache: dict[str, str] = {}
        self._empty_cache_saved_at: dict[tuple[str, str, str], float] = {}
        self._loaded_cache_keys: set[tuple[str, str, str]] = set()
        self.debug_context_id = _safe_hash(f"public-index:{time.time_ns()}")
        self._load_session_cookies()
        _debug(
            "initialized",
            context_id=self.debug_context_id,
            search_pages=self._search_pages,
            disk_cache=self._cache_path is not None,
        )

    def list_articles(
        self,
        *,
        nickname: str,
        alias: str,
        signature: str = "",
        expected_fakeid: str = "",
        begin: int,
        count: int,
    ) -> tuple[list[PublicArticle], int]:
        nickname = nickname.strip()
        alias = alias.strip()
        if not nickname:
            raise PublicIndexError("公开文章索引缺少公众号名称")

        requested_end = max(begin, 0) + max(count, 1)
        _debug(
            "list_articles_enter",
            context_id=self.debug_context_id,
            nickname_chars=len(nickname),
            alias_present=bool(alias),
            signature_present=bool(signature.strip()),
            expected_fakeid_hash=(
                _safe_hash(expected_fakeid) if expected_fakeid else ""
            ),
            begin=begin,
            count=count,
        )
        started_at = time.monotonic()
        candidates = self._discover(
            nickname=nickname,
            alias=alias,
            signature=signature,
            expected_fakeid=expected_fakeid,
            required_count=requested_end,
        )
        total = len(candidates)
        page = candidates[max(begin, 0):max(begin, 0) + max(count, 1)]
        articles: list[PublicArticle] = []
        for index, candidate in enumerate(page):
            was_cached = candidate.stable_id in self._resolved_cache
            try:
                link = self._resolve(candidate)
            except PublicIndexError:
                # One stale Sogou result should not discard the rest of the
                # page. A completely empty page is reported below.
                continue
            articles.append(
                PublicArticle(
                    aid=f"sogou:{candidate.stable_id}",
                    title=candidate.title,
                    link=link,
                    digest=candidate.digest,
                    cover=candidate.cover,
                    create_time=candidate.create_time,
                )
            )
            if not was_cached and index + 1 < len(page):
                self._resolve_delay()

        if page and not articles:
            _debug(
                "list_articles_resolve_failed",
                context_id=self.debug_context_id,
                candidate_count=len(page),
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
            )
            raise PublicIndexError("公开文章索引返回的链接已过期，请稍后重试")
        _debug(
            "list_articles_exit",
            context_id=self.debug_context_id,
            candidate_total=total,
            requested_candidates=len(page),
            resolved_articles=len(articles),
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        return articles, total

    def _discover(
        self,
        *,
        nickname: str,
        alias: str,
        signature: str,
        expected_fakeid: str,
        required_count: int,
    ) -> list[PublicArticleCandidate]:
        cache_key = (nickname, alias, expected_fakeid)
        cache_hash = _safe_hash("\u0000".join(cache_key))
        self._load_disk_cache(cache_key)
        empty_saved_at = self._empty_cache_saved_at.get(cache_key)
        if empty_saved_at is not None:
            if self._clock() - empty_saved_at <= EMPTY_CACHE_TTL_SECONDS:
                _debug(
                    "empty_cache_hit",
                    context_id=self.debug_context_id,
                    cache_hash=cache_hash,
                    age_seconds=int(self._clock() - empty_saved_at),
                )
                raise PublicIndexEmpty(
                    f"公开文章索引暂未收录“{nickname}”的文章"
                )
            self._empty_cache_saved_at.pop(cache_key, None)
        cached_candidates = self._candidate_cache.get(cache_key, [])
        if len(cached_candidates) >= max(required_count, 1):
            _debug(
                "candidate_cache_hit",
                context_id=self.debug_context_id,
                cache_hash=cache_hash,
                cached=len(cached_candidates),
                required=required_count,
            )
            return cached_candidates

        _debug(
            "discovery_start",
            context_id=self.debug_context_id,
            cache_hash=cache_hash,
            cached=len(cached_candidates),
            required=required_count,
        )

        queries = [value for value in (alias, nickname) if value]
        queries.extend(
            self._signature_search_queries(
                signature,
                nickname=nickname,
                alias=alias,
            )
        )
        seen_queries: set[str] = set()
        # A previous smaller request may have persisted only part of the
        # available result set. Seed discovery from it, but keep searching
        # when the current request asks for more articles.
        candidates_by_id: dict[str, PublicArticleCandidate] = {
            item.stable_id: item for item in cached_candidates
        }
        unverified_by_id: dict[str, PublicArticleCandidate] = {}
        search_request_count = 0
        parsed_candidate_count = 0
        exact_candidate_count = 0

        for query_index, query in enumerate(queries):
            if query in seen_queries:
                continue
            seen_queries.add(query)
            query_kind = (
                "alias"
                if alias and query == alias
                else "nickname"
                if query == nickname
                else "signature"
            )
            _debug(
                "query_start",
                context_id=self.debug_context_id,
                cache_hash=cache_hash,
                query_index=query_index,
                query_kind=query_kind,
                query_chars=len(query),
            )
            # Search results are relevance-ranked rather than chronological.
            # Scan several lightweight mobile pages, then sort by publication
            # time locally. An exact publisher-name filter below prevents a
            # same-keyword account from entering the selected account.
            for page in range(1, self._search_pages + 1):
                search_url = self._search_url(query, page)
                response = self._session.get(
                    SOGOU_SEARCH_URL,
                    params={
                        "type": 2,
                        "query": query,
                        "page": page,
                        "ie": "utf8",
                    },
                    timeout=20,
                    allow_redirects=True,
                )
                search_request_count += 1
                if response.status_code != 200:
                    raise PublicIndexError(
                        f"公开文章索引 HTTP {response.status_code}"
                    )
                source = response.text
                self._raise_for_challenge(source, str(response.url))
                all_parsed = self._parse_search_page(
                    source,
                    nickname=None,
                    referer=search_url,
                )
                parsed = [
                    item for item in all_parsed if item.publisher == nickname
                ]
                parsed_candidate_count += len(all_parsed)
                exact_candidate_count += len(parsed)
                for item in all_parsed:
                    previous = unverified_by_id.get(item.stable_id)
                    if previous is None or item.create_time >= previous.create_time:
                        unverified_by_id[item.stable_id] = item
                for item in parsed:
                    previous = candidates_by_id.get(item.stable_id)
                    if previous is None or item.create_time >= previous.create_time:
                        candidates_by_id[item.stable_id] = item
                if not parsed and page > 1:
                    break
                # The mobile index currently returns roughly ten results per
                # page. Two relevance-ranked pages give a useful freshness
                # window for the normal 1-10 article workflow. Continue only
                # when that window still has not produced enough exact-account
                # candidates (for example, large backward/audit requests).
                if (
                    page >= min(2, self._search_pages)
                    and len(candidates_by_id) >= max(required_count, 1)
                ):
                    break
                if page < self._search_pages:
                    self._delay()
            # Alias, nickname and signature searches often overlap. Stop only
            # when the requested window is filled; otherwise a cached or
            # relevance-ranked partial result would hide usable articles from
            # the remaining bounded queries.
            if len(candidates_by_id) >= max(required_count, 1):
                break

        _debug(
            "discovery_queries_done",
            context_id=self.debug_context_id,
            cache_hash=cache_hash,
            search_requests=search_request_count,
            parsed_candidates=parsed_candidate_count,
            exact_candidates=exact_candidate_count,
            unique_exact=len(candidates_by_id),
            unverified=len(unverified_by_id),
        )

        if not candidates_by_id and expected_fakeid:
            _debug(
                "rename_identity_probe_start",
                context_id=self.debug_context_id,
                cache_hash=cache_hash,
                expected_fakeid_hash=_safe_hash(expected_fakeid),
                unverified=len(unverified_by_id),
            )
            candidates_by_id = {
                item.stable_id: item
                for item in self._match_renamed_publisher(
                    unverified_by_id.values(),
                    expected_fakeid=expected_fakeid,
                )
            }

        candidates = sorted(
            candidates_by_id.values(),
            key=lambda item: (item.create_time, item.stable_id),
            reverse=True,
        )
        if not candidates:
            self._empty_cache_saved_at[cache_key] = self._clock()
            self._save_disk_cache(cache_key)
            _debug(
                "discovery_empty",
                context_id=self.debug_context_id,
                cache_hash=cache_hash,
                backend_fallback=False,
            )
            raise PublicIndexEmpty(
                f"公开文章索引暂未收录“{nickname}”的文章"
            )
        self._empty_cache_saved_at.pop(cache_key, None)
        self._candidate_cache[cache_key] = candidates
        self._save_disk_cache(cache_key)
        _debug(
            "discovery_done",
            context_id=self.debug_context_id,
            cache_hash=cache_hash,
            candidates=len(candidates),
        )
        return candidates

    @staticmethod
    def _signature_search_queries(
        signature: str,
        *,
        nickname: str,
        alias: str,
    ) -> list[str]:
        identity_terms = {
            value.strip()
            for value in (nickname, alias)
            if value and value.strip()
        }
        queries: list[str] = []
        seen: set[str] = set(identity_terms)
        clauses = re.split(r"[|｜,，。；;！!?？、：:\n\r]+", signature or "")
        for clause in clauses:
            compact = re.sub(r"\s+", "", clause).strip()
            if not compact:
                continue
            for identity in identity_terms:
                compact = compact.replace(identity, "")
            compact = compact.strip("-—_·~～")
            if len(compact) < 2:
                continue
            cjk_runs = re.findall(r"[\u3400-\u9fff]{2,}", compact)
            topic = (
                cjk_runs[0][:SIGNATURE_QUERY_LENGTH]
                if cjk_runs
                else compact[:SIGNATURE_QUERY_LENGTH]
            )
            if len(topic) < 2:
                continue
            query = f"{nickname} {topic}".strip()
            if query in seen:
                continue
            seen.add(query)
            queries.append(query)
            if len(queries) >= SIGNATURE_QUERY_LIMIT:
                break
        return queries

    def _match_renamed_publisher(
        self,
        candidates: Iterable[PublicArticleCandidate],
        *,
        expected_fakeid: str,
    ) -> list[PublicArticleCandidate]:
        """Match renamed accounts by the stable ``__biz`` in a public article.

        Sogou can keep an account's historical display name after WeChat has
        already renamed it. Verify one recent article per publisher group,
        then accept only the group whose public page belongs to the selected
        account's fakeid.
        """
        groups: dict[str, list[PublicArticleCandidate]] = {}
        ordered = sorted(
            candidates,
            key=lambda item: (item.create_time, item.stable_id),
            reverse=True,
        )
        for candidate in ordered:
            if candidate.publisher:
                groups.setdefault(candidate.publisher, []).append(candidate)

        # Broad signature searches can surface dozens of unrelated publishers.
        # Probe only the strongest repeated matches so this best-effort rename
        # fallback cannot turn one empty result into minutes of network waits.
        publisher_groups = sorted(
            groups.values(),
            key=lambda group: (
                len(group),
                group[0].create_time,
                group[0].stable_id,
            ),
            reverse=True,
        )[:RENAMED_PUBLISHER_GROUP_LIMIT]
        for index, group in enumerate(publisher_groups):
            try:
                link = self._resolve(
                    group[0],
                    timeout=RENAMED_PUBLISHER_PROBE_TIMEOUT_SECONDS,
                )
                response = self._session.get(
                    link,
                    timeout=RENAMED_PUBLISHER_PROBE_TIMEOUT_SECONDS,
                    allow_redirects=True,
                )
                if response.status_code != 200:
                    continue
                self._raise_for_challenge(response.text, str(response.url))
            except (PublicIndexError, OSError):
                pass
            else:
                if expected_fakeid in self._extract_public_article_fakeids(
                    response.text
                ):
                    return group
            if index + 1 < len(publisher_groups):
                self._resolve_delay()
        return []

    @staticmethod
    def _extract_public_article_fakeids(source: str) -> set[str]:
        patterns = (
            r"(?:[\"']?__biz[\"']?\s*[:=]\s*[\"']?)([A-Za-z0-9+/=]{8,})",
            r"\bvar\s+(?:biz|bizuin)\s*=\s*[\"']([A-Za-z0-9+/=]{8,})[\"']",
        )
        return {
            fakeid
            for pattern in patterns
            for fakeid in re.findall(pattern, source)
        }

    @staticmethod
    def _search_url(query: str, page: int) -> str:
        from urllib.parse import urlencode

        return f"{SOGOU_SEARCH_URL}?{urlencode({'type': 2, 'query': query, 'page': page, 'ie': 'utf8'})}"

    @staticmethod
    def _parse_search_page(
        source: str,
        *,
        nickname: str | None,
        referer: str,
    ) -> list[PublicArticleCandidate]:
        soup = BeautifulSoup(source, "lxml")
        candidates: list[PublicArticleCandidate] = []
        for item in soup.select("ul.news-list > li, li[id^='sogou_vr_11002601_box_']"):
            publisher = item.select_one(".s-p .all-time-y2, .time .s2")
            title_el = item.select_one("h3 a, h4 a")
            if not publisher or not title_el:
                continue
            publisher_name = publisher.get_text(strip=True)
            if nickname is not None and publisher_name != nickname:
                continue

            redirect_path = html_lib.unescape(title_el.get("href") or "")
            if not redirect_path.startswith("/link?"):
                continue
            mobile_timestamp = item.select_one(".time .s3")
            create_time = int(
                (mobile_timestamp.get("data-lastmodified") if mobile_timestamp else "")
                or 0
            )
            if not create_time:
                timestamp_el = item.select_one(".s-p .s2 script")
                timestamp_match = re.search(
                    r"timeConvert\(['\"](\d+)['\"]\)",
                    timestamp_el.get_text() if timestamp_el else "",
                )
                create_time = (
                    int(timestamp_match.group(1)) if timestamp_match else 0
                )
            raw_id = (item.get("d") or "").rsplit("-", 1)[-1]
            if not raw_id:
                raw_id = hashlib.sha256(
                    f"{title_el.get_text(strip=True)}\n{create_time}\n{redirect_path}".encode()
                ).hexdigest()[:32]

            digest_el = item.select_one(".txt-info, .list-txt > a")
            image_el = item.select_one(".img-box img, .pic img")
            cover = html_lib.unescape(image_el.get("src") or "") if image_el else ""
            if cover.startswith("//"):
                cover = f"https:{cover}"
            candidates.append(
                PublicArticleCandidate(
                    stable_id=raw_id,
                    title=title_el.get_text("", strip=True),
                    digest=(digest_el.get_text("", strip=True) if digest_el else ""),
                    cover=cover,
                    create_time=create_time,
                    redirect_url=urljoin(SOGOU_BASE, redirect_path),
                    referer=referer,
                    publisher=publisher_name,
                )
            )
        return candidates

    def _resolve(
        self,
        candidate: PublicArticleCandidate,
        *,
        timeout: float = 20,
    ) -> str:
        if candidate.stable_id in self._resolved_cache:
            _debug(
                "signed_link_cache_hit",
                context_id=self.debug_context_id,
                candidate_hash=_safe_hash(candidate.stable_id),
            )
            return self._resolved_cache[candidate.stable_id]

        _debug(
            "signed_link_resolve_start",
            context_id=self.debug_context_id,
            candidate_hash=_safe_hash(candidate.stable_id),
        )
        started_at = time.monotonic()
        response = self._session.get(
            candidate.redirect_url,
            headers={"Referer": candidate.referer},
            timeout=timeout,
            allow_redirects=False,
        )
        if response.status_code != 200:
            _debug(
                "signed_link_resolve_http_error",
                context_id=self.debug_context_id,
                candidate_hash=_safe_hash(candidate.stable_id),
                status=response.status_code,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
            )
            location = response.headers.get("location", "")
            self._raise_for_challenge(response.text, location)
            raise PublicIndexError(
                f"公开文章链接解析 HTTP {response.status_code}"
            )

        self._raise_for_challenge(response.text, str(response.url))
        segments = re.findall(
            r"url\s*\+=\s*(['\"])(.*?)\1\s*;?",
            response.text,
            flags=re.S,
        )
        # Do not run html.unescape() over the whole assembled URL. Python's
        # permissive entity parser treats the beginning of `&timestamp` as the
        # legacy `&times` entity, producing `×tamp` and a WeChat "Parameter
        # error" page. Decode only explicit ampersand entities emitted in the
        # script, preserving every query-parameter name byte-for-byte.
        link = "".join(segment for _, segment in segments)
        link = (
            link.replace("&amp;", "&")
            .replace("&#38;", "&")
            .replace("&#x26;", "&")
            .replace("@", "")
        )
        if not self._is_valid_wechat_link(link):
            _debug(
                "signed_link_resolve_invalid",
                context_id=self.debug_context_id,
                candidate_hash=_safe_hash(candidate.stable_id),
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
            )
            raise PublicIndexError("公开文章链接格式已变化")
        self._resolved_cache[candidate.stable_id] = link
        for cache_key in self._candidate_cache:
            if any(
                item.stable_id == candidate.stable_id
                for item in self._candidate_cache[cache_key]
            ):
                self._save_disk_cache(cache_key)
                break
        _debug(
            "signed_link_resolve_done",
            context_id=self.debug_context_id,
            candidate_hash=_safe_hash(candidate.stable_id),
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        return link

    def _load_disk_cache(self, cache_key: tuple[str, str, str]) -> None:
        if self._cache_path is None or cache_key in self._loaded_cache_keys:
            return
        self._loaded_cache_keys.add(cache_key)
        try:
            payload = json.loads(self._cache_path.read_text())
            entry = payload.get("entries", {}).get(self._cache_key(cache_key), {})
            saved_at = float(entry.get("saved_at", 0))
            if entry.get("status") == "empty":
                if self._clock() - saved_at <= EMPTY_CACHE_TTL_SECONDS:
                    self._empty_cache_saved_at[cache_key] = saved_at
                return
            if self._clock() - saved_at > CACHE_TTL_SECONDS:
                return
            candidates = [
                PublicArticleCandidate(**item)
                for item in entry.get("candidates", [])
                if isinstance(item, dict)
            ]
            if candidates:
                self._candidate_cache[cache_key] = candidates
            resolved = entry.get("resolved", {})
            if isinstance(resolved, dict):
                self._resolved_cache.update(
                    {
                        str(stable_id): str(link)
                        for stable_id, link in resolved.items()
                        if self._is_valid_wechat_link(str(link))
                    }
                )
        except (OSError, ValueError, TypeError):
            return

    def _save_disk_cache(self, cache_key: tuple[str, str, str]) -> None:
        if self._cache_path is None:
            return
        if cache_key in self._empty_cache_saved_at:
            entry = {
                "status": "empty",
                "saved_at": self._empty_cache_saved_at[cache_key],
                "candidates": [],
                "resolved": {},
            }
        elif cache_key in self._candidate_cache:
            candidate_ids = {
                item.stable_id for item in self._candidate_cache[cache_key]
            }
            entry = {
                "status": "ok",
                "saved_at": self._clock(),
                "candidates": [
                    asdict(item) for item in self._candidate_cache[cache_key]
                ],
                "resolved": {
                    stable_id: link
                    for stable_id, link in self._resolved_cache.items()
                    if stable_id in candidate_ids
                },
            }
        else:
            return
        try:
            payload = json.loads(self._cache_path.read_text())
            if not isinstance(payload, dict):
                payload = {}
        except (OSError, ValueError, TypeError):
            payload = {}
        entries = payload.setdefault("entries", {})
        entries[self._cache_key(cache_key)] = entry
        cookies = getattr(self._session, "cookies", None)
        if cookies is not None:
            sogou_cookies = self._sogou_cookie_dict(cookies)
            if sogou_cookies:
                payload["sogou_cookies"] = sogou_cookies
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False))
            temporary.replace(self._cache_path)
        except OSError:
            return

    def _load_session_cookies(self) -> None:
        if self._cache_path is None:
            return
        cookies = getattr(self._session, "cookies", None)
        if cookies is None or not hasattr(cookies, "update"):
            return
        try:
            payload = json.loads(self._cache_path.read_text())
            saved = payload.get("sogou_cookies", {})
            if isinstance(saved, dict):
                cookies.update(
                    {
                        str(name): str(value)
                        for name, value in saved.items()
                        if name and value
                    }
                )
        except (OSError, ValueError, TypeError):
            return

    @staticmethod
    def _sogou_cookie_dict(cookies) -> dict[str, str]:
        jar = getattr(cookies, "jar", None)
        if jar is not None:
            return {
                str(cookie.name): str(cookie.value)
                for cookie in jar
                if str(getattr(cookie, "domain", "")).lstrip(".").endswith(
                    "sogou.com"
                )
            }
        if not hasattr(cookies, "items"):
            return {}
        try:
            return {str(name): str(value) for name, value in cookies.items()}
        except (KeyError, ValueError):
            return {}

    @staticmethod
    def _cache_key(cache_key: tuple[str, str, str]) -> str:
        return "\u0000".join(cache_key)

    @staticmethod
    def _is_valid_wechat_link(link: str) -> bool:
        parsed = urlsplit(link)
        if parsed.scheme != "https" or parsed.netloc != "mp.weixin.qq.com":
            return False
        if parsed.path not in {"/s", "/s/"}:
            return False
        query = parse_qs(parsed.query)
        # Sogou's signed public links currently include all three fields. The
        # timestamp check also invalidates links written by the historical
        # `&timestamp`/`&times` decoding bug.
        return all(query.get(name) for name in ("src", "timestamp", "signature"))

    @staticmethod
    def _raise_for_challenge(source: str, url: str) -> None:
        markers = ("antispider", "请输入验证码", "访问过于频繁")
        if any(marker in source or marker in url for marker in markers):
            raise PublicIndexError("公开文章索引请求过于密集，请稍后重试")

    def _delay(self) -> None:
        if self._max_delay <= 0:
            return
        self._sleeper(random.uniform(self._min_delay, self._max_delay))

    def _resolve_delay(self) -> None:
        # Signed-link resolution is a short-lived public-index redirect, not a
        # WeChat backend list request. Keep it serialized with light jitter,
        # while avoiding several seconds of artificial latency for ten links.
        if self._resolve_max_delay <= 0:
            return
        self._sleeper(
            random.uniform(self._resolve_min_delay, self._resolve_max_delay)
        )
