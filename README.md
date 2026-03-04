基于《自主论》一书观点，在GPT辅助下编写的python小程序，包括20道题目，测试后给出评测结果。
欢迎大家一起来完善。

---

## 微信公众号合集下载并合并 PDF

新增脚本：`wechat_album_to_pdf.py`

功能：
- 输入公众号合集链接，自动分页拉取合集内所有文章；
- 抓取文章正文（`js_content`）；
- 自动合并成一个 PDF。

### 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 使用方法

```bash
python wechat_album_to_pdf.py "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxx&action=getalbum&album_id=xxx" -o "我的合集.pdf"
```

如果某些文章有访问限制，可以带上 Cookie：

```bash
python wechat_album_to_pdf.py "<合集链接>" --cookie "wxuin=...; pass_ticket=..." -o out.pdf
```

可选参数：
- `--keep-html`：保留中间 HTML 文件（默认会自动删除）。
