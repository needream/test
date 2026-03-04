#!/usr/bin/env python3
"""下载微信公众号合集文章并合并导出为一个 PDF。"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib import parse, request

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


@dataclass
class ArticleMeta:
    title: str
    url: str
    create_time: int


class WeChatAlbumDownloader:
    def __init__(self, album_url: str, cookie: str = "", timeout: int = 20) -> None:
        self.album_url = album_url
        self.cookie = cookie
        self.timeout = timeout
        self.biz, self.album_id = self._extract_album_params(album_url)

    @staticmethod
    def _extract_album_params(album_url: str) -> Tuple[str, str]:
        parsed = parse.urlparse(album_url)
        query = parse.parse_qs(parsed.query)
        biz = (query.get("__biz") or [""])[0]
        album_id = (query.get("album_id") or [""])[0]
        if not biz or not album_id:
            raise ValueError("合集链接缺少 __biz 或 album_id 参数。")
        return biz, album_id

    def _get(self, url: str, params: Dict[str, str]) -> str:
        query_url = f"{url}?{parse.urlencode(params)}"
        req = request.Request(query_url, method="GET")
        req.add_header("User-Agent", DEFAULT_UA)
        req.add_header("Referer", self.album_url)
        if self.cookie:
            req.add_header("Cookie", self.cookie)

        with request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="ignore")

    def fetch_album_articles(self) -> List[ArticleMeta]:
        """分页拉取合集里的文章列表。"""
        begin_msgid = ""
        begin_itemidx = ""
        articles: List[ArticleMeta] = []
        seen_urls = set()

        while True:
            params = {
                "__biz": self.biz,
                "action": "getalbum",
                "album_id": self.album_id,
                "count": "10",
                "f": "json",
                "begin_msgid": begin_msgid,
                "begin_itemidx": begin_itemidx,
            }
            body = self._get("https://mp.weixin.qq.com/mp/appmsgalbum", params)
            payload = json.loads(body)

            if payload.get("base_resp", {}).get("ret") not in (0, "0", None):
                err_msg = payload.get("base_resp", {}).get("err_msg", "未知错误")
                raise RuntimeError(f"拉取合集失败: {err_msg}")

            item_list = payload.get("getalbum_resp", {}).get("article_list", [])
            if not item_list:
                break

            for item in item_list:
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                articles.append(
                    ArticleMeta(
                        title=item.get("title") or "未命名文章",
                        url=url,
                        create_time=int(item.get("create_time") or 0),
                    )
                )

            continue_flag = payload.get("getalbum_resp", {}).get("continue_flag", "0")
            if str(continue_flag) != "1":
                break

            last = item_list[-1]
            begin_msgid = str(last.get("msgid") or "")
            begin_itemidx = str(last.get("itemidx") or "")
            if not begin_msgid:
                break

        if not articles:
            raise RuntimeError("未拿到任何文章，可能是链接无效、合集为空，或需要登录 Cookie。")

        return articles

    def fetch_article_content(self, article: ArticleMeta) -> Tuple[str, str]:
        html_text = self._get(article.url, {})

        title = _extract_by_regex(html_text, r"<title>(.*?)</title>") or article.title
        content = _extract_by_regex(
            html_text,
            r'<div[^>]*id="js_content"[^>]*>(.*?)</div>',
            flags=re.S,
        )

        if not content:
            raise RuntimeError(f"抓取文章失败（可能被限制访问）: {article.url}")

        return html.unescape(title.strip()), content.strip()


def _extract_by_regex(text: str, pattern: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1) if match else ""


def build_merged_html(downloader: WeChatAlbumDownloader, articles: Iterable[ArticleMeta]) -> str:
    blocks = []
    for idx, article in enumerate(articles, start=1):
        title, content = downloader.fetch_article_content(article)
        print(f"[{idx}] 已抓取: {title}")
        blocks.append(
            f"""
            <article class=\"doc-article\">
              <h1>{html.escape(title)}</h1>
              <p class=\"meta\"><a href=\"{html.escape(article.url)}\">原文链接</a></p>
              <div class=\"content\">{content}</div>
            </article>
            """
        )

    return f"""
    <!doctype html>
    <html lang=\"zh-CN\">
    <head>
      <meta charset=\"utf-8\" />
      <title>WeChat Album Export</title>
      <style>
        @page {{ size: A4; margin: 18mm 12mm; }}
        body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.7; color: #222; }}
        h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .meta {{ font-size: 12px; color: #666; margin-bottom: 14px; }}
        .doc-article {{ page-break-after: always; }}
        .doc-article:last-child {{ page-break-after: auto; }}
        img {{ max-width: 100%; height: auto; }}
        pre, code {{ white-space: pre-wrap; word-break: break-word; }}
      </style>
    </head>
    <body>
      {''.join(blocks)}
    </body>
    </html>
    """


async def html_to_pdf_via_playwright(html_file: Path, output_pdf: Path) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "缺少 playwright。请执行: pip install playwright && playwright install chromium"
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(html_file.resolve().as_uri(), wait_until="networkidle")
        await page.pdf(path=str(output_pdf), format="A4", print_background=True)
        await browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="下载微信公众号合集文章并合并为 PDF"
    )
    parser.add_argument("album_url", help="公众号合集链接")
    parser.add_argument(
        "-o",
        "--output",
        default="wechat_album.pdf",
        help="输出 PDF 文件路径（默认: wechat_album.pdf）",
    )
    parser.add_argument(
        "--cookie",
        default="",
        help="可选，访问受限文章时可提供 Cookie，例如 'wxuin=...; pass_ticket=...'",
    )
    parser.add_argument("--keep-html", action="store_true", help="保留中间 HTML 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    downloader = WeChatAlbumDownloader(args.album_url, cookie=args.cookie)
    articles = downloader.fetch_album_articles()
    print(f"共发现 {len(articles)} 篇文章，开始下载内容...")

    merged_html = build_merged_html(downloader, articles)
    output_pdf = Path(args.output).resolve()
    temp_html = output_pdf.with_suffix(".tmp.html")
    temp_html.write_text(merged_html, encoding="utf-8")

    try:
        asyncio.run(html_to_pdf_via_playwright(temp_html, output_pdf))
    finally:
        if not args.keep_html and temp_html.exists():
            temp_html.unlink()

    print(f"PDF 已生成: {output_pdf}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
