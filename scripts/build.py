"""Validate content and build a portable static site, using only the standard library."""
from __future__ import annotations
import argparse
import datetime
import html
import json
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from string import Template
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class ContentError(ValueError):
    pass


def schema_check(value, rule, location, schema):
    if "$ref" in rule:
        rule = schema["$defs"][rule["$ref"].rsplit("/", 1)[1]]
    kind = rule.get("type")
    valid_type = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
    }.get(kind, True)
    if not valid_type:
        raise ContentError(f"{location}: expected {kind}")
    if kind == "object":
        missing = set(rule.get("required", [])) - value.keys()
        extra = value.keys() - rule.get("properties", {}).keys()
        if missing:
            raise ContentError(f"{location}: missing {', '.join(sorted(missing))}")
        if extra and rule.get("additionalProperties") is False:
            raise ContentError(f"{location}: unexpected {', '.join(sorted(extra))}")
        for key, child in rule.get("properties", {}).items():
            if key in value:
                schema_check(value[key], child, f"{location}.{key}", schema)
    if kind == "array":
        if not rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", float("inf")):
            raise ContentError(f"{location}: invalid number of items")
        for index, child in enumerate(value):
            schema_check(child, rule["items"], f"{location}[{index}]", schema)
    if kind == "string":
        if not value.strip() or not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", float("inf")):
            raise ContentError(f"{location}: invalid text length")
        if "pattern" in rule and not re.fullmatch(rule["pattern"], value):
            raise ContentError(f"{location}: invalid format")
        if rule.get("format") == "date":
            try:
                if datetime.date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError as exc:
                raise ContentError(f"{location}: expected YYYY-MM-DD") from exc
    if kind == "integer" and not rule.get("minimum", -float("inf")) <= value <= rule.get("maximum", float("inf")):
        raise ContentError(f"{location}: out of range")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContentError(f"{path.name}: {exc}") from exc


def load_topics(root=ROOT):
    schema = read_json(root / "schemas/topic.schema.json")
    topics, orders, all_ids = [], set(), set()
    for path in sorted((root / "content").glob("*.json")):
        topic = read_json(path)
        schema_check(topic, schema, path.name, schema)
        if topic["slug"] != path.stem:
            raise ContentError(f"{path.name}: slug must match filename")
        if topic["order"] in orders:
            raise ContentError(f"{path.name}: duplicate order")
        orders.add(topic["order"])
        sections = {s["id"]: s for s in topic["sections"]}
        if len(sections) != len(topic["sections"]):
            raise ContentError(f"{path.name}: duplicate section id")
        questions = set()
        for card in topic["cards"]:
            if not re.fullmatch(re.escape(topic["slug"]) + r"-[0-9]{2}", card["id"]) or card["id"] in all_ids:
                raise ContentError(f"{path.name}: invalid or duplicate card id")
            all_ids.add(card["id"])
            if card["question"] in questions:
                raise ContentError(f"{path.name}: duplicate question")
            questions.add(card["question"])
            source = sections.get(card["source_id"])
            if not source or not any(card["evidence"] in p for p in source["paragraphs"]):
                raise ContentError(f"{path.name}/{card['id']}: evidence not found in source paragraph")
        for ref in topic["references"]:
            url = urlsplit(ref["url"])
            if url.scheme != "https" or not url.netloc or url.username or url.password:
                raise ContentError(f"{path.name}: invalid reference URL")
        topics.append(topic)
    if not topics:
        raise ContentError("content: at least one topic is required")
    return sorted(topics, key=lambda t: (t["order"], t["slug"]))


def esc(value):
    return html.escape(str(value), quote=True)


def json_script(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def tpl(root, name, **values):
    return Template((root / "templates" / name).read_text(encoding="utf-8")).substitute(values)


def cards_for(topics, prefix=""):
    result = []
    for topic in topics:
        for card in topic["cards"]:
            result.append(dict(card, topic=topic["slug"], topic_title=topic["title"],
                               source_url=f"{prefix}topics/{topic['slug']}.html#{card['source_id']}"))
    return result


def deck_markup(preview=False):
    label = "範例卡片" if preview else "複習卡"
    return f"""<section class="deck {'deck-preview' if preview else ''}" data-deck aria-label="{label}">
      <div class="deck-meta"><span data-deck-topic></span><span data-deck-counter></span></div>
      <div class="question-area"><span class="eyebrow">先試著回想</span><h2 data-question tabindex="-1"></h2></div>
      <button type="button" class="button button-dark reveal-button" data-reveal aria-expanded="false">顯示答案 <span aria-hidden="true">↗</span></button>
      <div class="answer-area" data-answer-area hidden><span class="eyebrow">參考答案</span><p data-answer></p>
      <details><summary>查看講義依據</summary><blockquote data-evidence></blockquote><a data-source>回到講義原文 <span aria-hidden="true">↗</span></a></details></div>
      <div class="self-rating" data-rating hidden><span>這張卡，掌握了嗎？</span><div><button type="button" class="button button-outline" data-rate="again">需再複習</button><button type="button" class="button button-green" data-rate="familiar">已熟悉 <span aria-hidden="true">✓</span></button></div></div>
      <div class="deck-controls"><button type="button" class="text-button" data-prev aria-label="上一張卡">← 上一張</button><span data-card-state></span><button type="button" class="text-button" data-next aria-label="下一張卡">下一張 →</button></div>
      <p class="empty-state" data-deck-empty hidden>目前沒有符合條件的卡片。可以切換主題或取消「只看需再複習」。</p>
      <p class="sr-only" data-deck-status role="status" aria-live="polite"></p>
    </section>"""


def shell(root, title, description, body, cards, prefix="", page="topics", count=0, all_ids=None):
    return tpl(root, "base.html", title=esc(title), description=esc(description), body=body,
               prefix=prefix, topics_active='class="active"' if page == "topics" else "",
               review_active='class="active" aria-current="page"' if page == "review" else "",
               about_active='class="active" aria-current="page"' if page == "about" else "",
               data=json_script(cards), total_cards=count, all_card_ids=json_script(all_ids or []))


def render_site(root=ROOT):
    topics = load_topics(root)
    all_cards = cards_for(topics)
    all_ids = [c["id"] for c in all_cards]
    count = len(all_cards)
    output = {}
    def add(name, text):
        output[name] = text.encode("utf-8")
    rows = []
    for index, topic in enumerate(topics, 1):
        search = esc(" ".join([topic["title"], topic["subtitle"], topic["category"]]))
        rows.append(f"""<article class="topic-row" data-topic-row data-search="{search}">
        <span class="topic-number">{index:02d}</span><div class="topic-copy"><span class="eyebrow">{esc(topic['category'])}</span>
        <h3><a href="topics/{topic['slug']}.html">{esc(topic['title'])}</a></h3><p>{esc(topic['subtitle'])}</p></div>
        <div class="topic-tail"><span>{topic['reading_minutes']} 分鐘閱讀 · {len(topic['cards'])} 張卡</span><a class="round-link" href="topics/{topic['slug']}.html" aria-label="閱讀{esc(topic['title'])}">↗</a></div></article>""")
    body = tpl(root, "index.html", rows="\n".join(rows), deck=deck_markup(True),
               topic_count=f"{len(topics):02d}", card_count=f"{count:02d}", first_slug=topics[0]["slug"])
    add("index.html", shell(root, "AI 學習筆記館", "用短篇講義理解 AI 概念，再以附原文依據的卡片自我複習。", body, all_cards[:1], count=count, all_ids=all_ids))
    for i, topic in enumerate(topics):
        prefix = "../"
        objectives = "".join(f"<li>{esc(x)}</li>" for x in topic["objectives"])
        toc = "".join(f'<a href="#{s["id"]}">{esc(s["title"])}</a>' for s in topic["sections"])
        sections = "".join(f'<section class="lesson-section" id="{s["id"]}"><span class="section-index">{j:02d}</span><h2>{esc(s["title"])}</h2>' +
                           "".join(f"<p>{esc(p)}</p>" for p in s["paragraphs"]) + "</section>" for j, s in enumerate(topic["sections"], 1))
        ex = topic["example"]
        example = f'<h2>{esc(ex["title"])}</h2><p>{esc(ex["scenario"])}</p><pre>{esc(ex["prompt"])}</pre><p>{esc(ex["explanation"])}</p>'
        misconceptions = "".join(f'<div class="misconception"><h3>{esc(m["myth"])}</h3><p>{esc(m["clarification"])}</p></div>' for m in topic["misconceptions"])
        references = "".join(f'<li><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{esc(r["title"])} ↗</a><span>{esc(r["publisher"])}</span></li>' for r in topic["references"])
        navigation = ""
        if i:
            prev = topics[i - 1]
            navigation += f'<a href="{prev["slug"]}.html"><span>上一篇</span>{esc(prev["title"])} ←</a>'
        if i + 1 < len(topics):
            nxt = topics[i + 1]
            navigation += f'<a class="next-topic" href="{nxt["slug"]}.html"><span>下一篇</span>{esc(nxt["title"])} →</a>'
        body = tpl(root, "topic.html", title=esc(topic["title"]), subtitle=esc(topic["subtitle"]),
                   category=esc(topic["category"]), reading_minutes=topic["reading_minutes"], updated=topic["updated"],
                   objectives=objectives, toc=toc, sections=sections, example=example,
                   misconceptions=misconceptions, references=references, deck=deck_markup(),
                   navigation=navigation, card_count=len(topic["cards"]))
        add(f"topics/{topic['slug']}.html", shell(root, topic["title"] + " — AI 學習筆記館", topic["subtitle"], body,
                                              cards_for([topic], prefix), prefix=prefix, count=count, all_ids=all_ids))
    options = '<option value="all">全部主題</option>' + "".join(f'<option value="{t["slug"]}">{esc(t["title"])}</option>' for t in topics)
    body = tpl(root, "review.html", options=options, deck=deck_markup(), card_count=count)
    add("review.html", shell(root, "翻卡複習 — AI 學習筆記館", "先回想答案，再揭示講義依據，記下自己的熟悉程度。", body, all_cards, page="review", count=count, all_ids=all_ids))
    project = read_json(root / "project.json")
    repo = project.get("repository_url", "")
    if repo and (urlsplit(repo).scheme != "https" or urlsplit(repo).hostname != "github.com"):
        raise ContentError("project.json: repository_url must be a GitHub HTTPS URL")
    repo_link = f'<a class="text-link" href="{esc(repo)}" target="_blank" rel="noopener noreferrer">GitHub 原始碼 ↗</a>' if repo else ""
    body = tpl(root, "about.html", repo_link=repo_link, topic_count=len(topics), card_count=count)
    add("about.html", shell(root, "關於本站 — AI 學習筆記館", "了解如何使用講義、翻卡與本機自評紀錄，以及本站的內容規則。", body, [], page="about", count=count, all_ids=all_ids))
    add("data/cards.json", json.dumps({"version": 1, "cards": all_cards}, ensure_ascii=False, indent=2) + "\n")
    add("project/AGENTS.md", (root / "AGENTS.md").read_text(encoding="utf-8"))
    for asset in ("styles.css", "site.js", "logo.svg"):
        output[f"assets/{asset}"] = (root / "assets" / asset).read_bytes()
    output[".nojekyll"] = b""
    check_links(output)
    return output, topics


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ContentError("duplicate HTML id: " + attrs["id"])
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])


def check_links(output):
    parsed = {}
    for name, data in output.items():
        if name.endswith(".html"):
            parser = LinkParser()
            parser.feed(data.decode("utf-8"))
            parsed[name] = parser
    for name, parser in parsed.items():
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                if url.scheme not in ("https", "mailto"):
                    raise ContentError(f"{name}: unsupported link {link}")
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path))) if url.path else name
            if target.startswith("../") or target not in output:
                raise ContentError(f"{name}: broken link {link}")
            if url.fragment and target in parsed and unquote(url.fragment) not in parsed[target].ids:
                raise ContentError(f"{name}: broken anchor {link}")


def write_site(output, destination):
    destination = destination.resolve()
    allowed = {ROOT.joinpath("docs").resolve(), ROOT.joinpath("dist").resolve()}
    if destination not in allowed:
        raise ContentError("Output must be the project's docs or dist directory")
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in output.items():
        target = destination / name
        if not target.resolve().is_relative_to(destination):
            raise ContentError("Output escaped destination")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    for target in destination.rglob("*"):
        if target.is_file() and target.relative_to(destination).as_posix() not in output:
            target.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed docs differ from generated output")
    parser.add_argument("--deploy", action="store_true", help="Also write a deployment copy to dist")
    args = parser.parse_args()
    try:
        output, topics = render_site()
        if args.check:
            actual = {p.relative_to(ROOT / "docs").as_posix(): p.read_bytes() for p in (ROOT / "docs").rglob("*") if p.is_file()}
            changed = sorted(k for k in actual.keys() | output.keys() if actual.get(k) != output.get(k))
            if changed:
                raise ContentError("Generated output is stale: " + ", ".join(changed))
        else:
            write_site(output, ROOT / "docs")
        if args.deploy:
            write_site(output, ROOT / "dist")
        print(json.dumps({"status": "passed", "topics": len(topics), "cards": sum(len(t["cards"]) for t in topics),
                          "pages": sum(k.endswith(".html") for k in output), "files": len(output),
                          "mode": "check" if args.check else "build"}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print("Build failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
