"""WeChat Official Account search and article-history client.

``searchbiz`` resolves the stable ``fakeid`` used as the account identity.
The logged-in account's own history comes from the backend publish-history
page. Other known accounts use a public article index and verify article
ownership against that stable identity; a ``fakeid`` is not treated as
permission to call a restricted cross-account backend list.
"""
from __future__ import annotations

import base64
import hashlib
import html as html_lib
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator

from curl_cffi import requests as cffi_requests

from . import config
from .article_list_cache import ArticleListCache
from .public_index import PublicIndexEmpty, SogouPublicIndex
from .request_guard import RequestCooldownError, RequestGuard

BASE = "https://mp.weixin.qq.com"
SEARCH_BIZ_URL = f"{BASE}/cgi-bin/searchbiz"
APPMSGPUBLISH_URL = f"{BASE}/cgi-bin/appmsgpublish"
ARTICLE_LIST_PAGE_SIZE = 5
BACKEND_ARTICLE_LIST_PAGE_SIZE = 20
OWN_HISTORY_PAGE_SIZE = 20
BROWSER_PROFILE = "chrome124"
ARTICLE_LIST_CACHE_SOURCE = "appmsgpublish-list-v1"

DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Origin": BASE,
    "Referer": f"{BASE}/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


class WCXError(Exception):
    """Base exception."""


class AuthError(WCXError):
    """Token/cookie invalid or expired."""


class RateLimitError(WCXError):
    """Hit WeChat frequency control (ret=200013)."""


class LocalCooldownError(RateLimitError):
    """A prior server limit blocked this request before it reached WeChat."""


class NotFoundError(WCXError):
    """No matching account."""


@dataclass
class Account:
    fakeid: str
    nickname: str
    alias: str = ""
    signature: str = ""
    round_head_img: str = ""

    def to_dict(self) -> dict:
        return {
            "fakeid": self.fakeid,
            "nickname": self.nickname,
            "alias": self.alias,
            "signature": self.signature,
            "round_head_img": self.round_head_img,
        }


@dataclass
class ArticleMeta:
    aid: str
    fakeid: str
    title: str
    link: str
    digest: str = ""
    cover: str = ""
    author: str = ""
    create_time: int = 0
    update_time: int = 0
    article_type: int | None = None
    copyright_type: int | None = None

    def to_dict(self) -> dict:
        return {
            "aid": self.aid,
            "fakeid": self.fakeid,
            "title": self.title,
            "link": self.link,
            "digest": self.digest,
            "cover": self.cover,
            "author": self.author,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "article_type": self.article_type,
            "copyright_type": self.copyright_type,
        }


def _format_retry_at(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%m月%d日 %H:%M:%S")


def _safe_hash(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def _debug(event: str, **fields: object) -> None:
    payload = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
        for key, value in fields.items()
    )
    suffix = f" {payload}" if payload else ""
    print(f"[DEBUG][wcx.fetcher] {event}{suffix}", file=sys.stderr, flush=True)


class Fetcher:
    def __init__(
        self,
        token: str,
        cookie: str,
        *,
        impersonate: str = BROWSER_PROFILE,
        session_marker: str | int | None = None,
        own_bizuin: str | int | None = None,
        request_guard: RequestGuard | None = None,
        pace_guard: RequestGuard | None = None,
        own_history_guard: RequestGuard | None = None,
        article_list_cache: ArticleListCache | None = None,
        public_index: SogouPublicIndex | None = None,
    ):
        self.token = token
        self.cookie = cookie
        self.impersonate = impersonate
        self.own_bizuin = str(own_bizuin or "").strip()
        # Authenticated request pacing follows the concrete login session.
        session_fingerprint = f"{token}\n{cookie}\n{session_marker or ''}".encode(
            "utf-8"
        )
        guard_key = hashlib.sha256(session_fingerprint).hexdigest()[:20]
        # One persistent pace guard serializes all authenticated requests. A
        # server cooldown is recorded against the specific source so a closed
        # cross-account list does not also block search or the account owner's
        # healthy publish-history page.
        self._pace_guard = pace_guard or request_guard or RequestGuard(
            config.REQUEST_GUARD_DB,
            f"wechat-session:{guard_key}:pace",
        )
        # This guard belongs only to the legacy appmsgpublish fallback. Never
        # inherit cooldowns from the retired /cgi-bin/appmsg list_ex route:
        # those rows describe a different capability and caused the previous
        # "re-login still loops" regression.
        self._request_guard = request_guard or RequestGuard(
            config.REQUEST_GUARD_DB,
            f"wechat-session:{guard_key}:external-publish-list",
        )
        self._search_guard = request_guard or RequestGuard(
            config.REQUEST_GUARD_DB,
            f"wechat-session:{guard_key}:search",
        )
        self._own_history_guard = own_history_guard or request_guard or RequestGuard(
            config.REQUEST_GUARD_DB,
            f"wechat-session:{guard_key}:own-history",
        )
        self._article_list_cache = article_list_cache or ArticleListCache(
            config.ARTICLE_LIST_CACHE_DB
        )
        self._public_index = public_index or SogouPublicIndex()
        self.article_index_source = "wechat"
        self.article_index_notice = ""
        self.debug_context_id = _safe_hash(f"{guard_key}:{time.time_ns()}")
        self._session = cffi_requests.Session(
            impersonate=impersonate,
            headers={
                **DEFAULT_HEADERS,
                "Cookie": cookie,
                "Referer": (
                    f"{BASE}/cgi-bin/home?t=home/index&lang=zh_CN&token={token}"
                ),
            },
        )
        _debug(
            "fetcher_initialized",
            context_id=self.debug_context_id,
            session_hash=_safe_hash(guard_key),
            own_bizuin_hash=_safe_hash(self.own_bizuin) if self.own_bizuin else "",
            public_index=type(self._public_index).__name__,
        )

    def _acquire(self, operation_guard: RequestGuard) -> None:
        try:
            operation_guard.check_cooldown()
            self._pace_guard.acquire()
        except RequestCooldownError as error:
            _debug(
                "authenticated_request_blocked_locally",
                context_id=self.debug_context_id,
                guard_hash=_safe_hash(operation_guard.key),
                retry_at=int(error.retry_at),
            )
            retry_at = _format_retry_at(error.retry_at)
            raise LocalCooldownError(
                "应用本地保护仍在生效，本次请求未发往微信。"
                f"应用最早会在 {retry_at} 允许再次尝试；"
                "这个时间由应用依据上一次 ret=200013 设置，"
                "不是微信给出的解封时间，重新登录也不会解除。"
            ) from error

    def _get_json(
        self,
        url: str,
        params: dict,
        *,
        operation_guard: RequestGuard,
        limit_label: str,
    ) -> dict:
        endpoint = url.removeprefix(BASE) or "/"
        _debug(
            "authenticated_json_request_start",
            context_id=self.debug_context_id,
            endpoint=endpoint,
            action=params.get("action") or params.get("sub_action") or params.get("sub"),
            fakeid_hash=_safe_hash(params.get("fakeid")) if params.get("fakeid") else "",
            begin=params.get("begin"),
            count=params.get("count"),
            query_chars=len(str(params.get("query") or "")),
            guard_hash=_safe_hash(operation_guard.key),
        )
        started_at = time.monotonic()
        self._acquire(operation_guard)
        resp = self._session.get(url, params=params, timeout=30)
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        if resp.status_code != 200:
            _debug(
                "authenticated_json_http_error",
                context_id=self.debug_context_id,
                endpoint=endpoint,
                status=resp.status_code,
                elapsed_ms=elapsed_ms,
            )
            raise WCXError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        ret = data.get("base_resp", {}).get("ret", 0)
        _debug(
            "authenticated_json_response",
            context_id=self.debug_context_id,
            endpoint=endpoint,
            status=resp.status_code,
            ret=ret,
            elapsed_ms=elapsed_ms,
        )
        if ret == 0:
            return data
        msg = data.get("base_resp", {}).get("err_msg", "")
        if ret == 200013:
            limited_at = _format_retry_at(time.time())
            cooldown = operation_guard.activate_cooldown()
            _debug(
                "authenticated_json_rate_limited",
                context_id=self.debug_context_id,
                endpoint=endpoint,
                guard_hash=_safe_hash(operation_guard.key),
                cooldown_until=int(cooldown.retry_at),
            )
            retry_at = _format_retry_at(cooldown.retry_at)
            detail = f"：{msg}" if msg else ""
            raise RateLimitError(
                f"微信{limit_label}于 {limited_at} 返回频率限制"
                f"（ret=200013）{detail}。"
                "该返回只针对当前接口；Chrome 或公众号后台首页正常打开与此不矛盾，"
                "也不代表登录公众号账号异常。"
                f"当前批次已停止。应用随后将该接口本地保护至 {retry_at}；"
                "这一小时是应用的保护策略，不是微信承诺的解封时刻，"
                "届时微信仍可能拒绝请求。"
                "已经写入本地的文章会保留。"
            )
        if ret in (200003, 200002, 200008):
            raise AuthError(f"Auth failed (ret={ret}): {msg}. Re-login needed.")
        raise WCXError(f"API error ret={ret}: {msg}")

    def _get_html(
        self,
        url: str,
        params: dict,
        *,
        operation_guard: RequestGuard,
    ) -> str:
        self._acquire(operation_guard)
        resp = self._session.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            raise WCXError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        source = resp.text
        if "publish_page =" in source or "publish_page_noencode =" in source:
            return source
        if any(marker in source for marker in ("扫码登录", "二维码登录", "login_frame")):
            raise AuthError("微信公众号登录已过期，请重新扫码登录")
        raise WCXError("微信后台发表记录页面缺少文章数据")

    def search_biz(self, query: str, *, begin: int = 0, count: int = 5) -> list[Account]:
        """Search accounts by name. Returns candidate list."""
        _debug(
            "search_biz_enter",
            context_id=self.debug_context_id,
            query_chars=len(query),
            begin=begin,
            count=count,
        )
        data = self._get_json(
            SEARCH_BIZ_URL,
            params={
                "action": "search_biz",
                "begin": begin,
                "count": count,
                "query": query,
                "token": self.token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": 1,
            },
            operation_guard=self._search_guard,
            limit_label="公众号搜索",
        )
        accounts = []
        for item in data.get("list", []):
            accounts.append(
                Account(
                    fakeid=item.get("fakeid", ""),
                    nickname=item.get("nickname", ""),
                    alias=item.get("alias", ""),
                    signature=item.get("signature", ""),
                    round_head_img=item.get("round_head_img", ""),
                )
            )
        _debug(
            "search_biz_exit",
            context_id=self.debug_context_id,
            result_count=len(accounts),
            result_id_hashes=[_safe_hash(account.fakeid) for account in accounts],
        )
        return accounts

    def resolve(self, query: str) -> Account:
        """Resolve name/fakeid to an account. Prefers exact nickname match."""
        results = self.search_biz(query)
        if not results:
            raise NotFoundError(f"No account found for: {query}")
        # exact match wins
        for acc in results:
            if acc.nickname == query or acc.alias == query or acc.fakeid == query:
                return acc
        return results[0]

    def list_articles(
        self,
        fakeid: str,
        *,
        begin: int = 0,
        count: int = ARTICLE_LIST_PAGE_SIZE,
        account: Account | None = None,
    ) -> tuple[list[ArticleMeta], int]:
        """Fetch one page of articles from the correct account-scoped source.

        `begin`/`count` address article units for public/external sources. The
        owner-history source addresses publish records; one multi-item record
        can therefore yield more than `count` articles.
        """
        # A resident Fetcher serves multiple accounts. Notices describe only
        # the current list operation and must never leak from a prior
        # public-index miss into a later own-account or legacy request.
        self.article_index_notice = ""
        own_account = self.is_own_account(fakeid)
        route = (
            "own-history"
            if own_account
            else "public-index"
            if account is not None and account.nickname.strip()
            else "public-index-metadata-error"
            if account is not None
            else "legacy-appmsgpublish"
        )
        _debug(
            "list_articles_route",
            context_id=self.debug_context_id,
            route=route,
            fakeid_hash=_safe_hash(fakeid),
            account_metadata=account is not None,
            nickname_chars=len(account.nickname.strip()) if account else 0,
            alias_present=bool(account and account.alias.strip()),
            begin=begin,
            count=count,
        )
        if own_account:
            self.article_index_source = "own-history"
            return self._list_own_articles(fakeid, begin=begin, count=count)
        return self._list_external_articles(
            fakeid,
            begin=begin,
            count=count,
            account=account,
        )

    def is_own_account(self, fakeid: str) -> bool:
        return bool(self.own_bizuin) and _decode_fakeid_bizuin(fakeid) == self.own_bizuin

    def _list_external_articles(
        self,
        fakeid: str,
        *,
        begin: int,
        count: int,
        account: Account | None,
    ) -> tuple[list[ArticleMeta], int]:
        if account is not None:
            nickname = account.nickname.strip()
            if not nickname:
                self.article_index_source = "public-metadata-error"
                self.article_index_notice = (
                    "已解析公众号缺少当前昵称，无法查询公开文章索引；"
                    "本次未请求微信公众号后台文章列表"
                )
                _debug(
                    "public_index_metadata_error",
                    context_id=self.debug_context_id,
                    fakeid_hash=_safe_hash(fakeid),
                    nickname_chars=0,
                    backend_fallback=False,
                )
                raise WCXError(self.article_index_notice)

            self.article_index_source = "public"
            self.article_index_notice = ""
            _debug(
                "public_index_request_start",
                context_id=self.debug_context_id,
                fakeid_hash=_safe_hash(fakeid),
                nickname_chars=len(nickname),
                alias_present=bool(account.alias.strip()),
                signature_present=bool(account.signature.strip()),
                begin=begin,
                count=count,
            )
            started_at = time.monotonic()
            try:
                rows, total = self._public_index.list_articles(
                    nickname=nickname,
                    alias=account.alias,
                    signature=account.signature,
                    expected_fakeid=fakeid,
                    begin=begin,
                    count=count,
                )
            except PublicIndexEmpty as error:
                self.article_index_source = "public-empty"
                self.article_index_notice = str(error)
                _debug(
                    "public_index_empty",
                    context_id=self.debug_context_id,
                    fakeid_hash=_safe_hash(fakeid),
                    elapsed_ms=int((time.monotonic() - started_at) * 1000),
                    backend_fallback=False,
                )
                return [], 0
            _debug(
                "public_index_request_done",
                context_id=self.debug_context_id,
                fakeid_hash=_safe_hash(fakeid),
                fetched=len(rows),
                total=total,
                elapsed_ms=int((time.monotonic() - started_at) * 1000),
                backend_fallback=False,
            )
            return (
                [
                    ArticleMeta(
                        aid=row.aid,
                        fakeid=fakeid,
                        title=row.title,
                        link=row.link,
                        digest=row.digest,
                        cover=row.cover,
                        author=account.nickname,
                        create_time=row.create_time,
                        update_time=row.create_time,
                        article_type=9,
                    )
                    for row in rows
                ],
                total,
            )

        # Only legacy callers that did not provide the resolved Account may
        # use the authenticated backend list. The desktop selected-account
        # flow always supplies Account, so a public-index miss cannot fall
        # through to this restricted capability.
        self.article_index_source = "wechat-id"
        return self._list_external_articles_from_wechat(
            fakeid,
            begin=begin,
            count=count,
        )

    def _list_external_articles_from_wechat(
        self,
        fakeid: str,
        *,
        begin: int,
        count: int,
    ) -> tuple[list[ArticleMeta], int]:
        page_count = min(max(count, 1), BACKEND_ARTICLE_LIST_PAGE_SIZE)
        cached = self._article_list_cache.get(fakeid, begin, page_count)
        if (
            cached is not None
            and cached.get("_wcx_article_list_source") == ARTICLE_LIST_CACHE_SOURCE
        ):
            self.article_index_source = "wechat-id-cache"
            _debug(
                "legacy_backend_cache_hit",
                context_id=self.debug_context_id,
                fakeid_hash=_safe_hash(fakeid),
                begin=begin,
                count=page_count,
            )
            return self._external_articles_from_payload(cached, fakeid)

        self.article_index_source = "wechat-id"
        _debug(
            "legacy_backend_fallback",
            context_id=self.debug_context_id,
            fakeid_hash=_safe_hash(fakeid),
            endpoint="/cgi-bin/appmsgpublish",
            begin=begin,
            count=page_count,
        )
        data = self._get_json(
            APPMSGPUBLISH_URL,
            params={
                "sub": "list",
                "search_field": "null",
                "begin": begin,
                "count": page_count,
                "query": "",
                "fakeid": fakeid,
                "type": "101_1",
                "free_publish_type": 1,
                "sub_action": "list_ex",
                "token": self.token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": 1,
            },
            operation_guard=self._request_guard,
            limit_label="公众号后台文章列表接口",
        )
        cache_payload = {
            **data,
            "_wcx_article_list_source": ARTICLE_LIST_CACHE_SOURCE,
        }
        self._article_list_cache.put(fakeid, begin, page_count, cache_payload)
        return self._external_articles_from_payload(cache_payload, fakeid)

    @staticmethod
    def _external_articles_from_payload(
        data: dict,
        fakeid: str,
    ) -> tuple[list[ArticleMeta], int]:
        page = data.get("publish_page")
        if isinstance(page, str):
            try:
                page = json.loads(html_lib.unescape(page)) if page else {}
            except json.JSONDecodeError as error:
                raise WCXError("微信公众号后台文章列表数据格式已变化") from error
        if not isinstance(page, dict):
            page = {}
        return Fetcher._articles_from_publish_page(page, fakeid)

    def _list_own_articles(
        self,
        fakeid: str,
        *,
        begin: int,
        count: int,
    ) -> tuple[list[ArticleMeta], int]:
        source = self._get_html(
            APPMSGPUBLISH_URL,
            params={
                "sub": "list",
                "begin": begin,
                "count": min(max(count, 1), OWN_HISTORY_PAGE_SIZE),
                "token": self.token,
                "lang": "zh_CN",
            },
            operation_guard=self._own_history_guard,
        )
        page = _extract_publish_page(source)
        return self._articles_from_publish_page(page, fakeid)

    @staticmethod
    def _articles_from_publish_page(
        page: dict,
        fakeid: str,
    ) -> tuple[list[ArticleMeta], int]:
        total = int(page.get("total_count", 0))
        articles: list[ArticleMeta] = []
        for entry in page.get("publish_list", []):
            info = entry.get("publish_info")
            if not info:
                continue
            if isinstance(info, str):
                info = json.loads(html_lib.unescape(info))
            article_type = _optional_int(info.get("type"))
            sent_time = (info.get("sent_info") or {}).get("time") or 0
            # WeChat currently returns either the newer `appmsg_info` shape or
            # the long-running `appmsgex` shape depending on account/session.
            # Normalize both so a backend rollout does not look like an empty
            # page to the caller.
            raw_articles = info.get("appmsg_info") or info.get("appmsgex") or []
            for art in raw_articles:
                if art.get("is_deleted"):
                    continue
                # Publish-only (not 群发) articles have no sent_info.time;
                # fall back to the per-article line_info.send_time.
                ts = (
                    sent_time
                    or (art.get("line_info") or {}).get("send_time")
                    or art.get("create_time")
                    or art.get("update_time")
                    or 0
                )
                aid = art.get("aid") or (
                    f"{art.get('appmsgid', '')}_{art.get('itemidx', 1)}"
                )
                articles.append(
                    ArticleMeta(
                        aid=str(aid),
                        fakeid=fakeid,
                        title=art.get("title", ""),
                        link=art.get("content_url") or art.get("link", ""),
                        digest=art.get("digest", ""),
                        cover=art.get("cover", ""),
                        author=art.get("author_name") or art.get("author", ""),
                        create_time=int(ts),
                        update_time=int(ts),
                        article_type=article_type,
                        copyright_type=_optional_int(art.get("copyright_type")),
                    )
                )
        return articles, total

    def iter_all_articles(
        self,
        fakeid: str,
        *,
        account: Account | None = None,
        max_items: int | None = None,
        page_size: int = ARTICLE_LIST_PAGE_SIZE,
        min_delay: float = 5.0,
        max_delay: float = 15.0,
        start_begin: int = 0,
        on_page: Callable[[int, int, int], None] | None = None,
    ) -> Iterator[ArticleMeta]:
        """Paginate through articles with polite delay.

        start_begin: server-side offset to start from (0 = newest).
        max_items: stop after this many yielded items (None = until total).
        on_page(begin, fetched_this_page, total) called after each page.
        """
        begin = start_begin
        effective_page_size = (
            OWN_HISTORY_PAGE_SIZE
            if self.is_own_account(fakeid)
            else BACKEND_ARTICLE_LIST_PAGE_SIZE
            if account is None
            else page_size
        )
        yielded = 0
        seen_aids: set[str] = set()
        while True:
            articles, total = self.list_articles(
                fakeid,
                begin=begin,
                count=effective_page_size,
                account=account,
            )
            if on_page:
                on_page(begin, len(articles), total)
            if not articles:
                break
            for art in articles:
                if art.aid in seen_aids:
                    continue
                seen_aids.add(art.aid)
                yield art
                yielded += 1
                if max_items and yielded >= max_items:
                    return
            begin += effective_page_size
            if begin >= total:
                break
            # Public-index pagination slices the already-discovered in-memory
            # result set. Sleeping here adds no network protection and made a
            # cached ten-article run look stalled.
            if self.article_index_source != "public":
                time.sleep(random.uniform(min_delay, max_delay))


def _decode_fakeid_bizuin(fakeid: str) -> str:
    value = (fakeid or "").strip()
    if not value:
        return ""
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded, validate=True).decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return ""
    return decoded if decoded.isdigit() else ""


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_publish_page(source: str) -> dict:
    decoder = json.JSONDecoder()
    for marker in ("publish_page_noencode =", "publish_page ="):
        offset = source.find(marker)
        if offset < 0:
            continue
        payload = source[offset + len(marker):].lstrip()
        try:
            page, _ = decoder.raw_decode(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(page, dict):
            return page
    raise WCXError("微信后台发表记录页面的数据格式已变化")
