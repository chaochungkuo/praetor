from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DOCS = ROOT / "docs"

PAGES = [
    ("README.md", "Overview"),
    ("ROADMAP.md", "Roadmap"),
    ("SECURITY.md", "Security"),
    ("CONTRIBUTING.md", "Contributing"),
    ("docs/INDEX.zh-TW.md", "Docs Index"),
    ("docs/PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md", "Open Source Success"),
    ("docs/PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md", "Public Security Review"),
    ("docs/PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md", "Privacy Boundaries"),
    ("docs/INSTALL_CHECKLIST.md", "Install Checklist"),
    ("docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md", "Deployment Security"),
    ("docs/PRAETOR_LOCAL_DEPLOY.md", "Local Deploy"),
    ("docs/PRAETOR_REMOTE_PRIVATE_DEPLOY.md", "Remote Private Deploy"),
    ("docs/PRAETOR_BACKUP_RESTORE.md", "Backup and Restore"),
    ("docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md", "Executor Bridge"),
    ("docs/PRAETOR_SYSTEM_SPEC.zh-TW.md", "System Spec"),
    ("docs/PRAETOR_UI_SPEC.zh-TW.md", "UI Spec"),
    ("docs/PRAETOR_REPO_ARCHITECTURE.zh-TW.md", "Repo Architecture"),
]


def slug_for(path: str) -> str:
    if path == "README.md":
        return "index.html"
    return path.replace("/", "__").removesuffix(".md") + ".html"


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_repl, escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _link_repl(match: re.Match[str]) -> str:
    label = match.group(1)
    target = html.unescape(match.group(2))
    if target.startswith(("http://", "https://", "#")):
        href = html.escape(target)
    else:
        normalized = target.lstrip("./")
        href = html.escape(slug_for(normalized) if normalized.endswith(".md") else target)
    return f'<a href="{href}">{label}</a>'


def markdown_to_html(markdown: str) -> str:
    html_lines: list[str] = []
    in_code = False
    in_list = False
    code_buffer: list[str] = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                html_lines.append("<pre><code>" + html.escape("\n".join(code_buffer)) + "</code></pre>")
                code_buffer = []
                in_code = False
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                in_code = True
            continue
        if in_code:
            code_buffer.append(line)
            continue
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            html_lines.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue
        item = re.match(r"^-\s+(.+)$", line)
        if item:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_markdown(item.group(1))}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{inline_markdown(line)}</p>")

    if in_code:
        html_lines.append("<pre><code>" + html.escape("\n".join(code_buffer)) + "</code></pre>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def page_template(title: str, body: str) -> str:
    nav = "\n".join(
        f'<a href="{slug_for(path)}">{html.escape(label)}</a>'
        for path, label in PAGES
        if (ROOT / path).exists()
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)} | Praetor</title>
    <link rel="stylesheet" href="assets/site.css" />
  </head>
  <body>
    <aside class="sidebar">
      <div class="brand">Praetor</div>
      <nav>{nav}</nav>
    </aside>
    <main class="content">
      {body}
    </main>
  </body>
</html>
"""


def write_css() -> None:
    assets = PUBLIC / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "site.css").write_text(
        """
:root {
  color-scheme: light dark;
  --bg: #f7f7f5;
  --panel: #ffffff;
  --text: #171717;
  --muted: #666;
  --line: #ddd9cf;
  --accent: #8f3f2a;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  border-right: 1px solid var(--line);
  padding: 28px 22px;
  background: var(--panel);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}
.brand {
  font-weight: 800;
  font-size: 22px;
  margin-bottom: 24px;
}
nav { display: grid; gap: 8px; }
nav a {
  color: var(--text);
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 8px;
}
nav a:hover { background: #eee9df; }
.content {
  width: min(960px, 100%);
  padding: 44px 36px 80px;
}
h1, h2, h3, h4 { line-height: 1.15; margin: 28px 0 12px; }
h1 { font-size: 42px; margin-top: 0; }
h2 { font-size: 28px; border-top: 1px solid var(--line); padding-top: 24px; }
p, li { line-height: 1.68; }
a { color: var(--accent); }
code {
  background: #eee9df;
  padding: 2px 5px;
  border-radius: 5px;
}
pre {
  background: #1d1d1b;
  color: #f4f0e8;
  padding: 18px;
  overflow: auto;
  border-radius: 8px;
}
@media (max-width: 820px) {
  body { display: block; }
  .sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .content { padding: 28px 20px 64px; }
  h1 { font-size: 34px; }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)
    write_css()
    for path, title in PAGES:
        source = ROOT / path
        if not source.exists():
            continue
        body = markdown_to_html(source.read_text(encoding="utf-8"))
        (PUBLIC / slug_for(path)).write_text(page_template(title, body), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
