# SEO 最新变化看板

这是一个每天自动更新的静态网页，用来汇总 SEO 相关公开 RSS 源中的最新文章标题和链接。

## 本地运行

先生成页面：

```bash
python fetch_seo_news.py
```

然后打开 `index.html` 即可查看。

## GitHub Pages 部署

1. 把这个仓库推到 GitHub。
2. 在仓库的 `Settings` 里打开 `Pages`。
3. 选择 `Deploy from a branch`。
4. 分支选 `main`，目录选 `/ (root)`。
5. 保存后，GitHub Pages 会开始发布这个静态页面。

## 自动更新

仓库里已经放了 GitHub Actions 工作流：

- 每天北京时间 9:30 自动运行
- 重新抓取 RSS
- 生成新的 `index.html`
- 如果内容有变化，就自动提交更新

对应的定时表达式是：

```text
cron: "30 1 * * *"
```

## 默认来源

当前默认抓取这几个 SEO 相关来源：

- Google Search Central
- Ahrefs Blog
- Search Engine Land
- Search Engine Journal

## 自定义来源

如果你想换成自己的 RSS 源，可以在 GitHub Actions 里设置环境变量 `SEO_FEEDS`，多个地址用英文逗号分隔。

例如：

```text
SEO_FEEDS=https://example.com/feed.xml,https://another.com/rss
```
