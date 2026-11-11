"""wcx CLI — the main user entry point.

Commands:
    wcx login              Set up token & cookie interactively
    wcx search <query>     Search accounts by name, pick one
    wcx list <query>       List articles (cached or fresh)
    wcx fetch <query>      Fetch full article list + contents
    wcx export <query>     Export cached articles to MD/HTML/JSON
    wcx status             Show config & cache stats
    wcx logout             Clear credentials
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import article as article_mod
from . import cache, config, fetcher

app = typer.Typer(
    help="wcx — 微信公众号文章抓取工具（本地 CLI，尊重频控）",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err = Console(stderr=True, style="red")
_RESIDENT_FETCHER_ENABLED = False
_RESIDENT_FETCHER_CACHE: tuple[tuple[object, ...], fetcher.Fetcher] | None = None


def _safe_hash(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def _debug(event: str, **fields: object) -> None:
    payload = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
        for key, value in fields.items()
    )
    suffix = f" {payload}" if payload else ""
    print(f"[DEBUG][wcx.cli] {event}{suffix}", file=sys.stderr, flush=True)


def _fetcher_context_id(instance: object) -> str:
    value = getattr(instance, "debug_context_id", "")
    return value if isinstance(value, str) and value else _safe_hash(id(instance))


def _version_callback(value: bool):
    if value:
        from . import __version__
        console.print(f"wcx {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback,
        is_eager=True, help="显示版本并退出。",
    ),
):
    """wcx — 微信公众号文章抓取工具。"""
    pass


def _get_fetcher() -> fetcher.Fetcher:
    creds = config.load_credentials()
    if not creds:
        err.print("[red]✗[/] 尚未登录。运行 [cyan]wcx login[/] 设置 token/cookie。")
        raise typer.Exit(1)
    return _fetcher_for_credentials(creds)


def _fetcher_for_credentials(creds: config.Credentials) -> fetcher.Fetcher:
    global _RESIDENT_FETCHER_CACHE

    own_bizuin = config.own_bizuin(creds)
    if _RESIDENT_FETCHER_ENABLED:
        key = (
            creds.token,
            creds.cookie,
            creds.last_login_at,
            own_bizuin,
        )
        if _RESIDENT_FETCHER_CACHE is not None:
            cached_key, cached_fetcher = _RESIDENT_FETCHER_CACHE
            if cached_key == key:
                _debug(
                    "resident_fetcher_reused",
                    context_id=_fetcher_context_id(cached_fetcher),
                    own_bizuin_hash=_safe_hash(own_bizuin) if own_bizuin else "",
                )
                return cached_fetcher

    instance = fetcher.Fetcher(
        creds.token,
        creds.cookie,
        session_marker=creds.last_login_at,
        own_bizuin=own_bizuin,
    )
    if _RESIDENT_FETCHER_ENABLED:
        _RESIDENT_FETCHER_CACHE = (key, instance)
    _debug(
        "fetcher_created",
        context_id=_fetcher_context_id(instance),
        resident=_RESIDENT_FETCHER_ENABLED,
        own_bizuin_hash=_safe_hash(own_bizuin) if own_bizuin else "",
        session_marker_present=creds.last_login_at is not None,
    )
    return instance


def _friendly_error(e: Exception) -> None:
    if isinstance(e, fetcher.AuthError):
        err.print(f"[red]✗ 认证失败：[/]{e}\n\n运行 [cyan]wcx login[/] 重新设置凭证。")
    elif isinstance(e, fetcher.LocalCooldownError):
        err.print(f"[yellow]本地保护：[/]{e}")
    elif isinstance(e, fetcher.RateLimitError):
        err.print(f"[red]✗ 触发风控：[/]{e}")
    elif isinstance(e, fetcher.NotFoundError):
        err.print(f"[yellow]? 找不到：[/]{e}")
    else:
        err.print(f"[red]✗ 错误：[/]{e}")


@app.command()
def login(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="后台 token"),
    cookie: Optional[str] = typer.Option(None, "--cookie", "-c", help="完整 Cookie"),
):
    """配置微信公众号后台 token 和 cookie（一次性，本地存储）。"""
    console.print(
        Panel.fit(
            "[bold]获取 token 和 cookie 的步骤：[/]\n"
            "1. 浏览器登录 [cyan]https://mp.weixin.qq.com[/]（需个人订阅号/服务号）\n"
            "2. 进入：[yellow]图文素材 → 新建图文 → 超链接 → 查找文章[/]\n"
            "3. 打开 DevTools（F12）→ Network\n"
            "4. 在搜索框搜任意账号，找到 [cyan]searchbiz[/] 请求\n"
            "5. 从 URL 复制 [cyan]token=XXXXX[/] 的值\n"
            "6. 从 Request Headers 复制完整 [cyan]Cookie[/] 字段",
            title="📘 登录指引",
            border_style="cyan",
        )
    )
    if not token:
        token = Prompt.ask("[bold]Token[/]").strip()
    if not cookie:
        cookie = Prompt.ask("[bold]Cookie[/]").strip()
    if not token or not cookie:
        err.print("[red]✗ token 和 cookie 不能为空[/]")
        raise typer.Exit(1)

    creds = config.Credentials(
        token=token,
        cookie=cookie,
        last_login_at=int(time.time()),
    )
    config.save_credentials(creds)
    console.print(f"[green]✓[/] 已保存到 [dim]{config.CONFIG_PATH}[/]")

    # smoke test
    try:
        f = _fetcher_for_credentials(creds)
        results = f.search_biz("人民日报")
        if results:
            console.print(f"[green]✓[/] 凭证有效（测试搜索返回 {len(results)} 条）")
    except Exception as e:
        err.print(f"[yellow]⚠ 凭证测试失败：[/]{e}")


@app.command()
def logout():
    """清除保存的凭证。"""
    if Confirm.ask("确认清除 token/cookie？", default=False):
        config.clear_credentials()
        console.print("[green]✓[/] 已清除")


@app.command()
def status():
    """显示配置和缓存状态。"""
    creds = config.load_credentials()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_row("配置目录", str(config.CONFIG_DIR))
    t.add_row("缓存数据库", str(config.CACHE_DB))
    t.add_row("登录状态", "[green]✓ 已登录[/]" if creds else "[red]✗ 未登录[/]")

    with cache.connect() as conn:
        n_acc = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        n_art = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        n_full = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE content_md IS NOT NULL"
        ).fetchone()[0]
    t.add_row("缓存账号数", str(n_acc))
    t.add_row("缓存文章数", f"{n_art}（含正文 {n_full}）")
    console.print(Panel(t, title="wcx status", border_style="cyan"))


@app.command()
def search(
    query: str = typer.Argument(..., help="公众号名称"),
):
    """搜索公众号，返回候选列表。"""
    try:
        f = _get_fetcher()
        results = f.search_biz(query)
    except Exception as e:
        _friendly_error(e)
        raise typer.Exit(1)

    if not results:
        console.print(f"[yellow]没有找到与 [bold]{query}[/] 匹配的公众号[/]")
        return

    t = Table(title=f"搜索：{query}", title_style="bold cyan")
    t.add_column("#", style="dim")
    t.add_column("昵称", style="bold")
    t.add_column("别名")
    t.add_column("fakeid", style="dim")
    t.add_column("简介")
    for i, acc in enumerate(results, 1):
        sig = (acc.signature or "").replace("\n", " ")
        if len(sig) > 40:
            sig = sig[:40] + "…"
        t.add_row(str(i), acc.nickname, acc.alias, acc.fakeid, sig)
    console.print(t)


@app.command()
def fetch(
    query: str = typer.Argument(..., help="公众号名称或 fakeid"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="最多抓取几篇"),
    with_content: bool = typer.Option(False, "--content", help="同时抓取正文"),
    page_size: int = typer.Option(
        fetcher.ARTICLE_LIST_PAGE_SIZE,
        "--page-size",
        help="公开索引页大小（默认 5；自有号后台自动使用 20）",
    ),
    min_delay: float = typer.Option(5.0, "--min-delay", help="最小请求间隔（秒）"),
    max_delay: float = typer.Option(15.0, "--max-delay", help="最大请求间隔（秒）"),
):
    """抓取公众号的文章列表（写入本地缓存）。"""
    try:
        f = _get_fetcher()
        account = f.resolve(query)
    except Exception as e:
        _friendly_error(e)
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold]{account.nickname}[/] [dim]({account.fakeid})[/]\n"
            f"{account.signature or '[dim]（无简介）[/dim]'}",
            title="🎯 目标账号",
            border_style="green",
        )
    )

    with cache.connect() as conn:
        cache.upsert_account(conn, account.to_dict())
        conn.commit()

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/]"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        task_id = None
        count = 0
        trace_id = _safe_hash(f"cli-fetch:{account.fakeid}:{time.time_ns()}")
        verified_public_html: dict[str, str] = {}

        def on_page(begin: int, fetched: int, total: int) -> None:
            nonlocal task_id
            if task_id is None:
                shown_total = min(total, limit) if limit else total
                task_id = progress.add_task(
                    f"抓取 [bold]{account.nickname}[/] 文章列表", total=shown_total
                )
            progress.update(task_id, advance=fetched)

        try:
            with progress:
                for art in f.iter_all_articles(
                    account.fakeid,
                    account=account,
                    max_items=limit,
                    page_size=page_size,
                    min_delay=min_delay,
                    max_delay=max_delay,
                    on_page=on_page,
                ):
                    if str(art.aid).startswith("sogou:"):
                        try:
                            public_html = article_mod.fetch_article_html(art.link)
                            identity = article_mod.extract_identity(public_html)
                            article_biz = identity.get("biz", "")
                            identity_matches = article_biz == account.fakeid
                            _debug(
                                "public_article_identity_check",
                                trace_id=trace_id,
                                aid_hash=_safe_hash(art.aid),
                                target_fakeid_hash=_safe_hash(account.fakeid),
                                article_biz_hash=(
                                    _safe_hash(article_biz) if article_biz else ""
                                ),
                                biz_present=bool(article_biz),
                                matches=identity_matches,
                                before_persist=True,
                                command="fetch",
                            )
                            if not identity_matches:
                                if article_biz:
                                    conn.execute(
                                        "DELETE FROM articles WHERE aid = ? AND fakeid = ?",
                                        (art.aid, account.fakeid),
                                    )
                                    conn.commit()
                                reason = (
                                    "文章公众号 ID 与目标账号不一致"
                                    if article_biz
                                    else "文章页未提供可核验的公众号 ID"
                                )
                                err.print(f"[yellow]跳过[/] {art.title}: {reason}")
                                continue
                            verified_public_html[art.aid] = public_html
                        except Exception as error:  # noqa: BLE001
                            _debug(
                                "public_article_identity_failed",
                                trace_id=trace_id,
                                aid_hash=_safe_hash(art.aid),
                                error_type=type(error).__name__,
                                error_chars=len(str(error)),
                                before_persist=True,
                                command="fetch",
                            )
                            err.print(
                                f"[yellow]跳过[/] {art.title}: "
                                f"文章归属校验失败：{error}"
                            )
                            continue
                        finally:
                            time.sleep(random.uniform(0.8, 1.8))
                    cache.upsert_article(conn, art.to_dict())
                    conn.commit()
                    count += 1
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ 已中断，已抓取的条目已保存到缓存[/]")
        except Exception as e:
            _friendly_error(e)
            console.print(f"[yellow]（已保存 {count} 条到缓存，可稍后续跑）[/]")
            raise typer.Exit(1)

        console.print(f"[green]✓[/] 已入库 [bold]{count}[/] 篇元数据")
        if f.article_index_notice:
            console.print(f"[yellow]{f.article_index_notice}；未请求后台跨公众号列表[/]")

        if with_content:
            rows = cache.list_articles(conn, account.fakeid, limit=limit)
            need = [r for r in rows if not (r["content_md"] or "").strip()]
            if not need:
                console.print("[dim]所有文章已有缓存正文[/]")
                return
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[cyan]{task.completed}/{task.total}[/]"),
                TimeElapsedColumn(),
                console=console,
            ) as prog:
                tid = prog.add_task("抓取正文", total=len(need))
                for r in need:
                    fetched_article_page = False
                    try:
                        html = verified_public_html.get(str(r["aid"]))
                        if html is None:
                            html = article_mod.fetch_article_html(r["link"])
                            fetched_article_page = True
                        if str(r["aid"]).startswith("sogou:"):
                            identity = article_mod.extract_identity(html)
                            article_biz = identity.get("biz", "")
                            identity_matches = article_biz == account.fakeid
                            _debug(
                                "public_article_identity_check",
                                trace_id=trace_id,
                                aid_hash=_safe_hash(r["aid"]),
                                target_fakeid_hash=_safe_hash(account.fakeid),
                                article_biz_hash=(
                                    _safe_hash(article_biz) if article_biz else ""
                                ),
                                biz_present=bool(article_biz),
                                matches=identity_matches,
                                before_persist=False,
                                command="fetch",
                            )
                            if not identity_matches:
                                if article_biz:
                                    conn.execute(
                                        "DELETE FROM articles WHERE aid = ? AND fakeid = ?",
                                        (r["aid"], account.fakeid),
                                    )
                                    conn.commit()
                                    raise RuntimeError(
                                        "公开索引文章与目标公众号 ID 不一致，已移除"
                                    )
                                raise RuntimeError(
                                    "公开索引文章无法确认公众号 ID，已跳过"
                                )
                        inner, md = article_mod.extract_content(html)
                        if not inner.strip() and not md.strip():
                            raise RuntimeError("解析出的正文为空")
                        cache.set_article_content(conn, r["aid"], inner, md)
                        conn.commit()
                    except Exception as e:  # noqa: BLE001
                        err.print(f"[red]✗[/] {r['title']}: {e}")
                    prog.update(tid, advance=1)
                    if fetched_article_page:
                        time.sleep(random.uniform(3.0, 7.0))


@app.command(name="list")
def list_cmd(
    query: str = typer.Argument(..., help="公众号名称或 fakeid"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示多少条"),
):
    """显示缓存中该公众号的文章列表。"""
    try:
        f = _get_fetcher()
        account = f.resolve(query)
    except Exception as e:
        _friendly_error(e)
        raise typer.Exit(1)

    with cache.connect() as conn:
        rows = cache.list_articles(conn, account.fakeid, limit=limit)

    if not rows:
        console.print(
            f"[yellow]缓存中没有 [bold]{account.nickname}[/] 的文章。"
            f"\n运行 [cyan]wcx fetch {query}[/] 开始抓取[/]"
        )
        return

    from datetime import datetime

    t = Table(title=f"{account.nickname} — 最近 {len(rows)} 篇", title_style="bold cyan")
    t.add_column("日期", style="dim")
    t.add_column("标题", style="bold")
    t.add_column("作者")
    t.add_column("正文", justify="center")
    for r in rows:
        date = datetime.fromtimestamp(r["create_time"]).strftime("%Y-%m-%d") if r["create_time"] else "-"
        has_content = "[green]✓[/]" if r["content_md"] else "[dim]·[/]"
        t.add_row(date, r["title"], r["author"] or "", has_content)
    console.print(t)


@app.command()
def export(
    query: str = typer.Argument(..., help="公众号名称或 fakeid"),
    out: Path = typer.Option(Path("./wcx-export"), "--out", "-o", help="输出目录"),
    fmt: str = typer.Option("all", "--format", "-f", help="索引格式：all|md|json|csv（默认 all 同时输出三种）"),
    articles_format: str = typer.Option(
        "md", "--articles", "-a", help="文章格式：md|html|none"
    ),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="仅导出最近 N 篇"),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="仅导出此日期之后发布的文章：YYYY-MM-DD 或相对值如 10d / 2w / 1m",
    ),
):
    """导出缓存中的文章到文件。"""
    from . import exporters

    try:
        f = _get_fetcher()
        account = f.resolve(query)
    except Exception as e:
        _friendly_error(e)
        raise typer.Exit(1)

    since_ts: Optional[int] = None
    if since:
        import re as _re
        from datetime import datetime as _dt, timedelta as _td

        m = _re.fullmatch(r"(\d+)([dwm])", since)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = _td(days=n * {"d": 1, "w": 7, "m": 30}[unit])
            since_ts = int((_dt.now() - delta).timestamp())
        else:
            try:
                since_ts = int(_dt.strptime(since, "%Y-%m-%d").timestamp())
            except ValueError:
                console.print(f"[red]--since 格式无效：{since}[/]")
                raise typer.Exit(1)

    with cache.connect() as conn:
        acc_row = cache.get_account(conn, account.fakeid)
        rows = cache.list_articles(conn, account.fakeid, limit=limit)

    if since_ts is not None:
        rows = [r for r in rows if (r["create_time"] or 0) >= since_ts]

    if not rows:
        console.print(
            f"[yellow]没有可导出的内容。先运行 [cyan]wcx fetch {query}[/][/]"
        )
        return

    target_dir = out / exporters._safe_filename(account.nickname)
    target_dir.mkdir(parents=True, exist_ok=True)

    with console.status(f"导出到 [cyan]{target_dir}[/] …", spinner="dots"):
        idx_path = exporters.export_index(rows, acc_row or account.to_dict(), target_dir, fmt=fmt)
        written = [idx_path]

        if articles_format != "none":
            art_dir = target_dir / "articles"
            for r in rows:
                if articles_format == "md":
                    written.append(exporters.export_article_markdown(r, art_dir))
                elif articles_format == "html":
                    written.append(exporters.export_article_html(r, art_dir))

    console.print(
        Panel.fit(
            f"[green]✓[/] 导出完成\n"
            f"目录：[cyan]{target_dir}[/]\n"
            f"索引：[dim]{idx_path.name}[/]\n"
            f"文章：[bold]{len(written) - 1}[/] 个文件",
            title="📦 导出",
            border_style="green",
        )
    )


@app.command()
def version():
    """显示版本。"""
    from . import __version__
    console.print(f"wcx {__version__}")


PROGRESS_PREFIX = "__WXMP_FETCH_PROGRESS__"
DAEMON_READY_PREFIX = "__WXMP_FETCH_DAEMON_READY__"
DAEMON_RESULT_PREFIX = "__WXMP_FETCH_DAEMON_RESULT__"


def _parse_date_range(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        start = datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError(f"日期格式应为 YYYY-MM-DD：{value}") from exc
    end = start + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())


@app.command(name="search-accounts-json")
def search_accounts_json(
    query: str = typer.Argument(..., help="公众号名称"),
):
    """搜索公众号，返回 JSON 数组（机器接口）。"""
    try:
        creds = config.load_credentials()
        if not creds:
            raise RuntimeError("尚未登录，请先扫码登录")
        f = _fetcher_for_credentials(creds)
        results = f.search_biz(query)
        print(json.dumps([acc.to_dict() for acc in results], ensure_ascii=False))
    except fetcher.AuthError as e:
        raise SystemExit(f"认证失败：{e}")
    except fetcher.LocalCooldownError as e:
        raise SystemExit(f"本地保护：{e}")
    except fetcher.RateLimitError as e:
        raise SystemExit(f"触发风控：{e}")
    except Exception as e:
        raise SystemExit(str(e))


@app.command(name="fetch-article-content-json")
def fetch_article_content_json(
    link: str = typer.Argument(..., help="文章 URL"),
):
    """抓取单篇文章正文，返回 JSON（机器接口）。"""
    try:
        print(
            json.dumps(_fetch_article_content_payload(link), ensure_ascii=False)
        )
    except Exception as e:
        raise SystemExit(str(e))


def _fetch_article_content_payload(link: str) -> dict[str, str]:
    html = article_mod.fetch_article_html(link)
    inner, md = article_mod.extract_content(html)
    return {"html": inner, "md": md}


@app.command(name="fetch-selected-account-json")
def fetch_selected_account_json(
    account_json: str = typer.Argument(..., help="账号 JSON 字符串"),
    limit: int = typer.Argument(
        ...,
        help="最多抓取篇数（forward/backward/classify）；audit 模式下作为已知区间上限的保险值",
    ),
    with_content: str = typer.Argument(..., help="是否抓取正文：0 或 1"),
    mode: str = typer.Option(
        "forward",
        "--mode",
        help="抓取方向：forward=从最新开始（默认），backward=从本地最老一篇之后继续向旧抓，audit=重扫已有区间并补漏，classify=重扫本地已有区间并回填分类",
    ),
    audit_date: str | None = typer.Option(
        None,
        "--audit-date",
        help="audit 模式下只检测指定日期当天的文章，格式 YYYY-MM-DD",
    ),
):
    """抓取指定公众号的文章列表+正文，带进度协议（机器接口）。"""

    def _text(value):
        return value or ""

    account = None  # forward-declare for emit
    count = 0
    content_count = 0
    classification_missing_before = 0
    classification_missing_after = 0
    trace_id = ""

    def emit(stage, status, message, current=None, total=None, title=None):
        print(PROGRESS_PREFIX + json.dumps({
            "fakeid": account.fakeid if account else "",
            "nickname": account.nickname if account else "",
            "stage": stage,
            "status": status,
            "message": message,
            "current": current,
            "total": total,
            "title": title,
        }, ensure_ascii=False), flush=True)

    try:
        payload = json.loads(account_json)
        fetch_limit = limit
        do_content = with_content == "1"
        mode_normalized = (mode or "forward").strip().lower()
        if mode_normalized not in {"forward", "backward", "audit", "classify"}:
            raise RuntimeError(f"未知抓取模式：{mode}")
        if audit_date and mode_normalized != "audit":
            raise RuntimeError("--audit-date 只能与 --mode audit 一起使用")
        audit_range = (
            _parse_date_range(audit_date) if mode_normalized == "audit" else None
        )

        creds = config.load_credentials()
        if not creds:
            raise RuntimeError("尚未登录，请先扫码登录")

        account = fetcher.Account(
            fakeid=_text(payload.get("fakeid")).strip(),
            nickname=_text(payload.get("nickname")).strip(),
            alias=_text(payload.get("alias")).strip(),
            signature=_text(payload.get("signature")).strip(),
            round_head_img=_text(
                payload.get("avatar") or payload.get("round_head_img")
            ).strip(),
        )
        if not account.fakeid or not account.nickname:
            raise RuntimeError("公众号选择缺少 fakeid 或昵称")

        trace_id = _safe_hash(f"{account.fakeid}:{time.time_ns()}")
        _debug(
            "selected_account_fetch_enter",
            trace_id=trace_id,
            fakeid_hash=_safe_hash(account.fakeid),
            nickname_chars=len(account.nickname),
            alias_present=bool(account.alias),
            signature_present=bool(account.signature),
            limit=fetch_limit,
            with_content=do_content,
            mode=mode_normalized,
        )

        audit_date_label = audit_date.strip() if audit_date else ""
        target_desc = f"，检测日期={audit_date_label}" if audit_date_label else ""
        emit(
            "prepare",
            "done",
            f"已确认目标公众号：{account.nickname}（mode={mode_normalized}{target_desc}）",
        )

        f = _fetcher_for_credentials(creds)
        _debug(
            "selected_account_fetcher_ready",
            trace_id=trace_id,
            fetcher_context_id=_fetcher_context_id(f),
            own_account=f.is_own_account(account.fakeid),
        )
        with cache.connect() as conn:
            emit("account", "running", "正在准备账号信息")
            cache.upsert_account(conn, account.to_dict())
            emit("account", "done", "账号信息已准备，等待文章列表确认")

            local_count = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE fakeid = ?",
                (account.fakeid,),
            ).fetchone()[0]
            local_aids: set[str] = {
                row[0]
                for row in conn.execute(
                    "SELECT aid FROM articles WHERE fakeid = ?",
                    (account.fakeid,),
                ).fetchall()
            }
            classification_missing_before = conn.execute(
                """
                SELECT COUNT(*) FROM articles
                WHERE fakeid = ?
                  AND (article_type IS NULL OR copyright_type IS NULL)
                """,
                (account.fakeid,),
            ).fetchone()[0]

            if mode_normalized == "forward":
                start_begin = 0
                page_max_items = fetch_limit
                article_total = fetch_limit
                stage_label = "向前续抓"
            elif mode_normalized == "backward":
                start_begin = local_count
                page_max_items = fetch_limit
                article_total = fetch_limit
                stage_label = "向后续抓"
            elif mode_normalized == "classify":
                if local_count <= 0:
                    raise RuntimeError("当前公众号没有可回填分类的本地文章")
                start_begin = 0
                page_max_items = min(local_count, fetch_limit)
                article_total = page_max_items
                stage_label = "旧数据分类回填"
            else:  # audit
                start_begin = 0
                page_max_items = (
                    fetch_limit if audit_range else max(local_count, fetch_limit)
                )
                article_total = (
                    page_max_items if audit_range else max(local_count, fetch_limit)
                )
                stage_label = (
                    f"完备性检测 {audit_date_label} 当天"
                    if audit_range
                    else "完备性回扫"
                )

            def on_page(begin, fetched, total):
                nonlocal article_total
                if mode_normalized == "audit":
                    article_total = max(min(total, page_max_items), 1)
                elif mode_normalized == "classify":
                    article_total = page_max_items
                else:
                    article_total = min(total, fetch_limit) if fetch_limit else total
                source_label = {
                    "public": "公开文章索引",
                    "public-empty": "公开文章索引",
                    "own-history": "公众号后台发表记录",
                    "wechat-id": "后台文章列表",
                    "wechat-id-cache": "后台缓存列表",
                }.get(f.article_index_source, "文章索引")
                _debug(
                    "article_page_received",
                    trace_id=trace_id,
                    fetcher_context_id=_fetcher_context_id(f),
                    source=f.article_index_source,
                    begin=begin,
                    fetched=fetched,
                    total=total,
                )
                emit(
                    "articles",
                    "running",
                    f"{stage_label}：{source_label}已读取 {fetched} 篇",
                    count,
                    article_total,
                )

            emit(
                "articles",
                "running",
                (
                    f"{stage_label}：读取当前公众号后台发表记录"
                    if f.is_own_account(account.fakeid)
                    else f"{stage_label}：正在读取公开文章索引并校验公众号 ID"
                ),
                0,
                article_total,
            )

            new_inserts = 0
            matched_count = 0
            matched_aids: list[str] = []
            verified_public_html: dict[str, str] = {}
            for art in f.iter_all_articles(
                account.fakeid,
                account=account,
                max_items=page_max_items,
                # External public discovery uses small five-article pages;
                # the account owner's publish-history source selects its own
                # twenty-record page size inside Fetcher.
                page_size=fetcher.ARTICLE_LIST_PAGE_SIZE,
                start_begin=start_begin,
                on_page=on_page,
            ):
                count += 1
                if audit_range:
                    day_start, day_end = audit_range
                    if art.create_time >= day_end:
                        emit(
                            "articles",
                            "running",
                            f"{stage_label}：已扫描 {count}/{article_total}，等待进入当天区间",
                            count,
                            article_total,
                            art.title,
                        )
                        continue
                    if art.create_time < day_start:
                        emit(
                            "articles",
                            "running",
                            f"{stage_label}：已越过当天边界",
                            count,
                            article_total,
                            art.title,
                        )
                        break

                if str(art.aid).startswith("sogou:"):
                    try:
                        emit(
                            "articles",
                            "running",
                            f"{stage_label}：正在用公众号 ID 校验文章归属",
                            count,
                            article_total,
                            art.title,
                        )
                        public_html = article_mod.fetch_article_html(art.link)
                        identity = article_mod.extract_identity(public_html)
                        article_biz = identity.get("biz", "")
                        identity_matches = article_biz == account.fakeid
                        _debug(
                            "public_article_identity_check",
                            trace_id=trace_id,
                            aid_hash=_safe_hash(art.aid),
                            target_fakeid_hash=_safe_hash(account.fakeid),
                            article_biz_hash=(
                                _safe_hash(article_biz) if article_biz else ""
                            ),
                            biz_present=bool(article_biz),
                            matches=identity_matches,
                            before_persist=True,
                        )
                        if not identity_matches:
                            # A previous buggy build may already have stored
                            # this Sogou candidate under the selected account.
                            # Remove only a positively identified mismatch;
                            # an absent biz is inconclusive and must not erase
                            # existing user data.
                            if article_biz:
                                conn.execute(
                                    "DELETE FROM articles WHERE aid = ? AND fakeid = ?",
                                    (art.aid, account.fakeid),
                                )
                                conn.commit()
                                local_aids.discard(art.aid)
                            reason = (
                                "文章公众号 ID 与所选账号不一致"
                                if article_biz
                                else "文章页未提供可核验的公众号 ID"
                            )
                            emit(
                                "articles",
                                "warning",
                                f"{stage_label}：{reason}，未写入本地",
                                count,
                                article_total,
                                art.title,
                            )
                            continue
                        verified_public_html[art.aid] = public_html
                    except Exception as error:
                        _debug(
                            "public_article_identity_failed",
                            trace_id=trace_id,
                            aid_hash=_safe_hash(art.aid),
                            error_type=type(error).__name__,
                            error_chars=len(str(error)),
                            before_persist=True,
                        )
                        emit(
                            "articles",
                            "warning",
                            f"{stage_label}：文章归属校验失败，未写入本地：{error}",
                            count,
                            article_total,
                            art.title,
                        )
                        continue
                    finally:
                        time.sleep(random.uniform(0.8, 1.8))

                is_new = art.aid not in local_aids
                cache.upsert_article(conn, art.to_dict())
                conn.commit()
                matched_count += 1
                matched_aids.append(art.aid)
                if is_new:
                    local_aids.add(art.aid)
                    new_inserts += 1
                progress_detail = (
                    f"匹配 {matched_count} 篇，新增 {new_inserts} 篇"
                    if mode_normalized != "classify"
                    else f"已更新 {matched_count} 篇元数据"
                )
                emit(
                    "articles",
                    "running",
                    f"{stage_label}：已扫描 {count}/{article_total}，{progress_detail}",
                    count,
                    article_total,
                    art.title,
                )

            article_index_notice = f.article_index_notice
            if article_index_notice:
                next_action = (
                    "已保留现有文章，并继续处理尚未下载的正文"
                    if do_content and local_count > 0
                    else "已保存公众号；可稍后重试，或改用文章链接录入"
                )
                _debug(
                    "article_index_unavailable",
                    trace_id=trace_id,
                    fetcher_context_id=_fetcher_context_id(f),
                    source=f.article_index_source,
                    backend_fallback=False,
                    local_article_count=local_count,
                )
                emit(
                    "articles",
                    "warning",
                    f"{article_index_notice}；{next_action}",
                    count,
                    article_total,
                )

            if mode_normalized == "classify" and page_max_items >= local_count:
                unmatched_rows = [
                    row
                    for row in conn.execute(
                        """
                        SELECT aid, title, link FROM articles
                        WHERE fakeid = ?
                          AND (article_type IS NULL OR copyright_type IS NULL)
                        ORDER BY create_time DESC
                        """,
                        (account.fakeid,),
                    ).fetchall()
                    if row["aid"] not in matched_aids
                ]
                if unmatched_rows:
                    emit(
                        "articles",
                        "running",
                        f"{stage_label}：{len(unmatched_rows)} 篇未出现在发表记录，改从原文页补充",
                        count,
                        article_total,
                    )
                for index, row in enumerate(unmatched_rows):
                    try:
                        html = article_mod.fetch_article_html(row["link"])
                        classification = article_mod.extract_classification(html)
                        article_type = classification["article_type"]
                        copyright_type = classification["copyright_type"]
                        if article_type is None and copyright_type is None:
                            raise RuntimeError("原文页未提供分类字段")
                        conn.execute(
                            """
                            UPDATE articles
                            SET article_type = COALESCE(?, article_type),
                                copyright_type = COALESCE(?, copyright_type)
                            WHERE aid = ?
                            """,
                            (article_type, copyright_type, row["aid"]),
                        )
                        conn.commit()
                        emit(
                            "articles",
                            "running",
                            f"{stage_label}：原文页分类已更新 {index + 1}/{len(unmatched_rows)}",
                            count,
                            article_total,
                            row["title"],
                        )
                    except Exception as error:
                        emit(
                            "articles",
                            "warning",
                            f"{stage_label}：原文页分类不可用：{error}",
                            count,
                            article_total,
                            row["title"],
                        )
                    if index + 1 < len(unmatched_rows):
                        time.sleep(random.uniform(0.8, 1.8))

            classification_missing_after = conn.execute(
                """
                SELECT COUNT(*) FROM articles
                WHERE fakeid = ?
                  AND (article_type IS NULL OR copyright_type IS NULL)
                """,
                (account.fakeid,),
            ).fetchone()[0]
            if mode_normalized == "classify":
                filled = max(
                    classification_missing_before - classification_missing_after,
                    0,
                )
                done_msg = (
                    f"{stage_label}完成：扫描 {count} 篇，"
                    f"补齐 {filled} 篇，仍缺 {classification_missing_after} 篇"
                )
            else:
                done_msg = (
                    f"{article_index_notice}；已保留现有数据"
                    if article_index_notice
                    else (
                        f"{stage_label}完成：扫描 {count} 篇，"
                        f"{'新增' if mode_normalized != 'audit' else '补漏'} {new_inserts} 篇"
                    )
                )
            if audit_range:
                done_msg = (
                    f"{stage_label}完成：扫描 {count} 篇，"
                    f"当天 {matched_count} 篇，补漏 {new_inserts} 篇"
                )
            emit(
                "articles",
                "done",
                done_msg,
                count,
                article_total,
            )

            if do_content:
                if audit_range:
                    placeholders = ",".join("?" for _ in matched_aids)
                    rows = (
                        conn.execute(
                            f"SELECT * FROM articles WHERE aid IN ({placeholders}) ORDER BY create_time DESC",
                            matched_aids,
                        ).fetchall()
                        if matched_aids
                        else []
                    )
                else:
                    rows = cache.list_articles(conn, account.fakeid, limit=fetch_limit)
                need = [r for r in rows if not (r["content_md"] or "").strip()]
                emit(
                    "content",
                    "running",
                    f"待抓取正文 {len(need)} 篇",
                    0,
                    len(need),
                )
                for row in need:
                    fetched_article_page = False
                    try:
                        emit(
                            "content",
                            "running",
                            f"正在抓取正文 {content_count + 1}/{len(need)}",
                            content_count,
                            len(need),
                            row["title"],
                        )
                        html = verified_public_html.get(str(row["aid"]))
                        if html is None:
                            html = article_mod.fetch_article_html(row["link"])
                            fetched_article_page = True
                        if str(row["aid"]).startswith("sogou:"):
                            identity = article_mod.extract_identity(html)
                            article_biz = identity.get("biz", "")
                            _debug(
                                "public_article_identity_check",
                                trace_id=trace_id,
                                aid_hash=_safe_hash(row["aid"]),
                                target_fakeid_hash=_safe_hash(account.fakeid),
                                article_biz_hash=(
                                    _safe_hash(article_biz) if article_biz else ""
                                ),
                                biz_present=bool(article_biz),
                                matches=bool(article_biz) and article_biz == account.fakeid,
                                before_persist=False,
                            )
                            if article_biz != account.fakeid:
                                if article_biz:
                                    conn.execute(
                                        "DELETE FROM articles WHERE aid = ? AND fakeid = ?",
                                        (row["aid"], account.fakeid),
                                    )
                                    conn.commit()
                                    raise RuntimeError(
                                        "公开索引文章与目标公众号 ID 不一致，已移除"
                                    )
                                raise RuntimeError(
                                    "公开索引文章无法确认公众号 ID，已保留现有数据"
                                )
                        inner, md = article_mod.extract_content(html)
                        if not inner.strip() and not md.strip():
                            raise RuntimeError("解析出的正文为空")
                        cache.set_article_content(conn, row["aid"], inner, md)
                        conn.commit()
                        content_count += 1
                        emit(
                            "content",
                            "running",
                            f"正文已写入 {content_count}/{len(need)}",
                            content_count,
                            len(need),
                            row["title"],
                        )
                    except Exception as e:
                        _debug(
                            "article_content_failed",
                            trace_id=trace_id,
                            aid_hash=_safe_hash(row["aid"]),
                            error_type=type(e).__name__,
                            error_chars=len(str(e)),
                        )
                        emit(
                            "content",
                            "warning",
                            f"正文抓取失败：{e}",
                            content_count,
                            len(need),
                            row["title"],
                        )
                        print(f"{row['title']}: {e}", file=sys.stderr)
                    if fetched_article_page:
                        time.sleep(random.uniform(0.8, 1.8))
                emit(
                    "content",
                    "done",
                    f"正文抓取完成 {content_count}/{len(need)} 篇",
                    content_count,
                    len(need),
                )

        action_word = "补漏" if mode_normalized == "audit" else "新增"
        complete_message = (
            f"已保存公众号并保留现有数据：正文 {content_count} 篇"
            if article_index_notice
            else (
                f"已完成（mode={mode_normalized}）：扫描 {count} 篇，"
                f"{action_word} {new_inserts} 篇，正文 {content_count} 篇"
            )
        )
        if mode_normalized == "classify":
            filled = max(
                classification_missing_before - classification_missing_after,
                0,
            )
            complete_message = (
                f"已完成（mode={mode_normalized}）：扫描 {count} 篇，"
                f"补齐分类 {filled} 篇，仍缺 {classification_missing_after} 篇"
            )
        if audit_range:
            complete_message = (
                f"已完成（mode={mode_normalized}, audit_date={audit_date_label}）："
                f"扫描 {count} 篇，当天 {matched_count} 篇，补漏 {new_inserts} 篇，正文 {content_count} 篇"
            )
        emit(
            "complete",
            "done",
            complete_message,
            count,
            count,
        )
        _debug(
            "selected_account_fetch_exit",
            trace_id=trace_id,
            source=f.article_index_source,
            scanned=count,
            inserted=new_inserts,
            content_saved=content_count,
            index_status="unavailable" if article_index_notice else "ready",
        )
        print(json.dumps({
            "fakeid": account.fakeid,
            "nickname": account.nickname,
            "mode": mode_normalized,
            "audit_date": audit_date_label or None,
            "scanned": count,
            "matched_count": matched_count,
            "new_inserts": new_inserts,
            "classification_missing_before": classification_missing_before,
            "classification_missing_after": classification_missing_after,
            "count": count,  # kept for backwards compat
            "content_count": content_count,
            "article_index_status": (
                "unavailable" if article_index_notice else "ready"
            ),
            "article_index_notice": article_index_notice or None,
        }, ensure_ascii=False))
    except fetcher.AuthError as e:
        _debug("selected_account_fetch_error", trace_id=trace_id, category="auth")
        raise SystemExit(f"认证失败：{e}")
    except fetcher.LocalCooldownError as e:
        _debug("selected_account_fetch_error", trace_id=trace_id, category="local-cooldown")
        raise SystemExit(
            f"本地保护：{e} 本次已保存文章列表 {count} 篇、正文 {content_count} 篇。"
        )
    except fetcher.RateLimitError as e:
        _debug("selected_account_fetch_error", trace_id=trace_id, category="rate-limit")
        raise SystemExit(
            f"触发风控：{e} 本次已保存文章列表 {count} 篇、正文 {content_count} 篇。"
        )
    except Exception as e:
        _debug(
            "selected_account_fetch_error",
            trace_id=trace_id,
            category="unexpected",
            error_type=type(e).__name__,
            error_chars=len(str(e)),
        )
        raise SystemExit(str(e))


@app.command(name="serve-fetch-json")
def serve_fetch_json():
    """常驻处理桌面端请求，避免每个操作重新解包并初始化引擎。"""
    global _RESIDENT_FETCHER_ENABLED, _RESIDENT_FETCHER_CACHE

    _RESIDENT_FETCHER_ENABLED = True
    _RESIDENT_FETCHER_CACHE = None
    print(DAEMON_READY_PREFIX, flush=True)
    try:
        for raw_line in sys.stdin:
            request_id = ""
            operation = "unknown"
            request_started_at = time.monotonic()
            try:
                request = json.loads(raw_line)
                request_id = str(request.get("request_id") or "")
                operation = str(
                    request.get("operation") or "fetch_selected_account"
                )
                account_payload_for_log = request.get("account")
                account_fakeid_for_log = (
                    str(account_payload_for_log.get("fakeid") or "")
                    if isinstance(account_payload_for_log, dict)
                    else ""
                )
                _debug(
                    "daemon_request_received",
                    request_id=request_id,
                    operation=operation,
                    account_fakeid_hash=(
                        _safe_hash(account_fakeid_for_log)
                        if account_fakeid_for_log
                        else ""
                    ),
                    limit=request.get("limit"),
                    with_content=bool(request.get("with_content")),
                    mode=request.get("mode"),
                    link_hash=(
                        _safe_hash(request.get("link"))
                        if request.get("link")
                        else ""
                    ),
                )
                if operation == "search_accounts":
                    query = str(request.get("query") or "").strip()
                    if not query:
                        raise RuntimeError("公众号搜索请求缺少名称")
                    creds = config.load_credentials()
                    if not creds:
                        raise RuntimeError("尚未登录，请先扫码登录")
                    results = _fetcher_for_credentials(creds).search_biz(query)
                    print(
                        json.dumps(
                            [account.to_dict() for account in results],
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                elif operation == "fetch_selected_account":
                    account_payload = request.get("account")
                    if not isinstance(account_payload, dict):
                        raise RuntimeError("抓取请求缺少公众号信息")
                    fetch_selected_account_json(
                        account_json=json.dumps(
                            account_payload,
                            ensure_ascii=False,
                        ),
                        limit=int(request.get("limit") or 10),
                        with_content="1" if request.get("with_content") else "0",
                        mode=str(request.get("mode") or "forward"),
                        audit_date=request.get("audit_date"),
                    )
                elif operation == "fetch_article_content":
                    link = str(request.get("link") or "").strip()
                    if not link:
                        raise RuntimeError("正文抓取请求缺少文章链接")
                    print(
                        json.dumps(
                            _fetch_article_content_payload(link),
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                else:
                    raise RuntimeError(f"未知常驻引擎操作：{operation}")
                result = {"request_id": request_id, "status": "ok"}
            except SystemExit as exc:
                result = {
                    "request_id": request_id,
                    "status": "error",
                    "error": str(exc.code or "抓取任务失败"),
                }
            except Exception as exc:
                result = {
                    "request_id": request_id,
                    "status": "error",
                    "error": str(exc),
                }
            _debug(
                "daemon_request_finished",
                request_id=request_id,
                operation=operation,
                status=result["status"],
                elapsed_ms=int((time.monotonic() - request_started_at) * 1000),
            )
            print(
                DAEMON_RESULT_PREFIX + json.dumps(result, ensure_ascii=False),
                flush=True,
            )
    finally:
        _RESIDENT_FETCHER_ENABLED = False
        _RESIDENT_FETCHER_CACHE = None


if __name__ == "__main__":
    app()
