import json
import subprocess
from pathlib import Path

from scripts.heo import only_synced
from scripts.heo.content import Item, dump, parse
from scripts.heo.publish import payload
from scripts.heo.sync_flickr import select_albums
from scripts.heo.validate import validate


def test_repository_content_is_valid():
    assert validate() == []


def test_round_trip_keeps_fields_and_body():
    text = "---\nsource_id: talk:x\ntitle: A talk\ndate: '2024-01-02'\nevent: Conf\n---\n\nAbstract here.\n"
    item = parse(text, Path("content/_talks/x.md"))
    assert item.meta["event"] == "Conf"
    assert parse(dump(item), item.path).meta == item.meta
    assert parse(dump(item), item.path).body == "Abstract here."


def test_hash_ignores_nothing_published():
    a = parse("---\nsource_id: project:a\ntitle: A\nera: civic\n---\n", Path("content/_projects/a.md"))
    b = parse("---\nsource_id: project:a\ntitle: A\nera: civic\nsummary: new\n---\n", Path("content/_projects/a.md"))
    assert a.content_hash() != b.content_hash()


def _album(aid, title):
    return {"id": aid, "title": {"_content": title}}


def test_flickr_selection_rule():
    albums = [
        _album("1", "2024-10-13 Acadia"),
        _album("2", "2026-06-30 Goshen Scout Camp"),
        _album("3", "New Zealand"),
        _album("4", "2024"),
        _album("5", "Christmas 2012"),
    ]
    chosen = select_albums(albums, exclude={"2": ""}, include={"3": ""})
    assert [a["id"] for a in chosen] == ["1", "3"]


def test_payload_maps_type_fields_and_hidden():
    item = Item(
        path=Path("content/_photos/acadia-2024.md"),
        meta={"source_id": "flickr:1", "title": "Acadia", "flickr_id": "1", "hidden": True,
              "synced": {"cover_url": "https://example.com/c.jpg", "count": 3}},
    )
    body = payload(item, "draft")
    assert body["type"] == "photo_album"
    assert body["hidden"] is True
    assert body["meta"]["flickr_id"] == "1"
    assert json.loads(body["meta"]["synced"])["count"] == 3
    assert body["featured_image_url"] == "https://example.com/c.jpg"


def test_markdown_body_is_rendered_and_html_body_is_kept():
    md = Item(path=Path("content/_posts/a.md"), meta={"source_id": "a:1", "title": "A", "date": "2024-01-01"}, body="Some *text*")
    html = Item(path=Path("content/_posts/b.md"), meta={"source_id": "b:1", "title": "B", "date": "2024-01-01", "format": "html"}, body="<!-- wp:paragraph --><p>x</p>")
    assert "<em>text</em>" in payload(md, "draft")["content"]
    assert payload(html, "draft")["content"] == "<!-- wp:paragraph --><p>x</p>"


def test_only_synced_detects_curated_changes(tmp_path, monkeypatch):
    def run(*args):
        subprocess.run(args, cwd=tmp_path, check=True, capture_output=True)

    f = tmp_path / "content" / "_projects" / "a.md"
    f.parent.mkdir(parents=True)
    f.write_text("---\nsource_id: project:a\ntitle: A\nera: civic\nsynced:\n  stars: 1\n---\n")
    run("git", "init", "-q", "-b", "main")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "init", "--allow-empty")
    run("git", "add", ".")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    run("git", "checkout", "-qb", "sync")
    monkeypatch.chdir(tmp_path)

    f.write_text("---\nsource_id: project:a\ntitle: A\nera: civic\nsynced:\n  stars: 2\n---\n")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "stars")
    assert only_synced.main(["main", "sync"]) == 0

    f.write_text("---\nsource_id: project:a\ntitle: A renamed\nera: civic\nsynced:\n  stars: 2\n---\n")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "title")
    assert only_synced.main(["main", "sync"]) == 1


def test_import_cleans_wordpress_slugs():
    from scripts.heo.import_wordpress import clean_slug, norm_title
    assert clean_slug("professional-civic-engineering%ef%bf%bc") == "professional-civic-engineering"
    assert clean_slug("2012") == "2012"
    assert norm_title("CrisisCommons &amp; Congress") == norm_title("crisiscommons & congress")


def _page(tags, status):
    return {"properties": {
        "Tags": {"type": "multi_select", "multi_select": [{"name": t} for t in tags]},
        "Status": {"type": "status", "status": {"name": status} if status else None},
    }}


def test_notion_selection_needs_blog_and_published():
    from scripts.heo.sync_notion import is_published
    assert is_published(_page(["Blog"], "Published"))
    assert is_published(_page(["blog", "published"], "Draft"))
    assert not is_published(_page(["Blog"], "Draft"))
    assert not is_published(_page(["Journal"], "Published"))


def test_notion_blocks_to_markdown():
    from scripts.heo.sync_notion import Converter

    def rt(text, **ann):
        return [{"type": "text", "plain_text": text, "annotations": ann, "href": ann.pop("href", None)}]

    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": rt("Intro")}},
        {"type": "paragraph", "paragraph": {"rich_text": rt("Hello ") + rt("world", bold=True)}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt("one")},
         "children": [{"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt("nested")}}]},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt("two")}},
        {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rt("first")}},
        {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rt("second")}},
        {"type": "code", "code": {"language": "python", "rich_text": rt("print(1)")}},
        {"id": "abc-1", "type": "image", "image": {"type": "file", "file": {"url": "https://s3/x.png"}, "caption": []}},
        {"type": "child_page", "child_page": {"title": "skip me"}},
    ]
    md = Converter(lambda url, bid: f"/assets/notion/{bid}.png").convert(blocks)
    assert md == (
        "## Intro\n\n"
        "Hello **world**\n\n"
        "- one\n\n    - nested\n- two\n\n"
        "1. first\n2. second\n\n"
        "```python\nprint(1)\n```\n\n"
        "![](/assets/notion/abc-1.png)"
    )


def test_portfolio_rule_applies_to_own_repositories_only():
    from scripts.heo.content import portfolio_excluded
    assert portfolio_excluded({"github": "ajturner/geopress", "synced": {"topics": ["wordpress"]}})
    assert not portfolio_excluded({"github": "ajturner/geopress", "synced": {"topics": ["Portfolio"]}})
    assert not portfolio_excluded({"github": "koopjs/koop", "synced": {"topics": []}})
    assert not portfolio_excluded({"title": "No repo"})


FEED = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"
 xmlns:media="http://search.yahoo.com/mrss/"><title>Andrew Turner Talks</title>
<entry><yt:videoId>zYSEOML_0Xo</yt:videoId><title>GeoAI and the Future of Mapping: Implications for 21st-Century Digital Resilience</title>
<author><name>National Academies</name></author><published>2023-05-22T18:00:00+00:00</published>
<media:group><media:thumbnail url="https://i.ytimg.com/vi/zYSEOML_0Xo/hqdefault.jpg"/><media:description>Workshop talk.</media:description></media:group></entry>
</feed>"""


def _talk(stem, **meta):
    return Item(path=Path(f"content/_talks/{stem}.md"), meta={"source_id": f"talk:{stem}", "date": "2020-01-01", "event": "X", **meta})


def test_youtube_feed_and_page_parsing():
    from scripts.heo.sync_youtube import parse_feed, playlist_page_ids

    (v,) = parse_feed(FEED)
    assert v["id"] == "zYSEOML_0Xo" and v["published_at"] == "2023-05-22" and v["channel"] == "National Academies"
    assert v["description"] == "Workshop talk." and v["thumbnail"].endswith("hqdefault.jpg")
    page = ('"url":"/watch?v=w3C1lRx0k44\\u0026list=PLX\\u0026index=1" href="/watch?v=DTU_jSWpQPE&amp;list=PLX" '
            '"/watch?v=w3C1lRx0k44&list=PLX" "/watch?v=zzzzzzzzzzz" "/watch?v=yyyyyyyyyyy&list=PLOTHER"')
    assert playlist_page_ids(page, "PLX") == ["w3C1lRx0k44", "DTU_jSWpQPE"]


def test_youtube_video_matches_talk_by_id_map_or_title():
    from scripts.heo.sync_youtube import match_talk, normalize

    by_id = _talk("a", title="Something Else", youtube_id="AAAAAAAAAAA")
    mapped = _talk("b", title="Where 2.0 That Matters")
    titled = _talk("c", title="Lessons Learned from Neogeography")
    short = _talk("d", title="Hub")
    talks = [by_id, mapped, titled, short]
    mapping = {"w3C1lRx0k44": "talk:b"}

    def video(vid, title):
        return {"id": vid, "title": title, "published_at": "", "channel": "", "description": "", "thumbnail": ""}

    assert match_talk(video("AAAAAAAAAAA", "Anything"), talks, mapping) is by_id
    assert match_talk(video("w3C1lRx0k44", 'Where 2.0 2010: Andrew Turner, "Crisis Mapping"'), talks, mapping) is mapped
    assert match_talk(video("Ci3R-Kx9ODw", "Lessons Learned from Neogeography Applied to GIS"), talks, mapping) is titled
    assert match_talk(video("BBBBBBBBBBB", "Hub"), talks, mapping) is None  # too short to trust
    assert match_talk(video("CCCCCCCCCCC", "An Unrelated Keynote"), talks, mapping) is None
    assert normalize('Where 09:  Andrew Turner, "Are Geospatial Tools..." #esri') == "where 09 are geospatial tools"


def test_youtube_map_points_at_existing_talks():
    from scripts.heo.content import iter_items
    from scripts.heo.sync_youtube import video_map

    ids = {i.meta["source_id"] for i in iter_items(["_talks"])}
    missing = {v: s for v, s in video_map().items() if s not in ids}
    assert missing == {}


def test_github_discovery_labels_and_drafts():
    from scripts.heo.sync_github import discovery

    def repo(name, **kw):
        return {"full_name": f"ajturner/{name}", "fork": False, "private": False, "topics": [], "pushed_at": "2020-01-01", "has_pages": False, **kw}

    covered = {"ajturner/plan-stuff-a-thon"}
    args = dict(covered=covered, cutoff="2026-01-01", recent=True, pages=True, topics=["portfolio"])
    assert discovery(repo("holocene", topics=["history", "portfolio"]), **args) == "labeled"
    assert discovery(repo("plan-stuff-a-thon", topics=["portfolio"]), **args) is None  # excluded wins
    assert discovery(repo("fieldkey", topics=["portfolio"], private=True), **args) is None
    assert discovery(repo("site", has_pages=True), **args) == "found"
    assert discovery(repo("fresh", pushed_at="2026-06-01"), **args) == "found"
    assert discovery(repo("old"), **args) is None
    assert discovery(repo("tagged", topics=["portfolio"]), **{**args, "topics": []}) is None


def test_notion_filter_uses_existing_blog_option():
    from scripts.heo.sync_notion import blog_filter

    def schema(*opts):
        return {"properties": {"Tags": {"type": "multi_select", "multi_select": {"options": [{"name": o} for o in opts]}}}}

    assert blog_filter(schema("Journal", "Work")) is None
    assert blog_filter(schema("Journal", "blog")) == {"property": "Tags", "multi_select": {"contains": "blog"}}
    assert blog_filter(schema("Blog", "BLOG")) == {"or": [
        {"property": "Tags", "multi_select": {"contains": "Blog"}},
        {"property": "Tags", "multi_select": {"contains": "BLOG"}},
    ]}


def test_flickr_cover_is_never_a_private_photo():
    from scripts.heo.sync_flickr import cover_url

    album = {"primary": "9", "server": "1", "secret": "s"}
    grid = [{"src": "https://live.staticflickr.com/1/2_x_b.jpg"}]
    assert cover_url(album, {"url_l": "PRIVATE"}, {"2", "3"}, grid) == grid[0]["src"]
    assert cover_url(album, {"url_l": "PUBLIC"}, {"9", "2"}, grid) == "PUBLIC"
    assert cover_url(album, {}, set(), []) == ""


GENERATED = """I'm increasingly convinced the most interesting form factor for AI isn't another screen.

It's the opposite: a computer you don't touch.

A pendant is not a phone replacement. It's not a smart speaker. It's not a chatbot.

## What it is

- A searchable timeline of the day
- Lightweight summaries
- Extracted commitments
- Context for the next conversation

That's it.

## Why now

- Transcription was too expensive
- Retrieval was too hard
- The output wasn't shaped for action

## Closing thought

The scarce resource isn't information.

It's continuity.
""" * 2


def test_voice_check_flags_generated_rhythm_and_passes_his_posts(tmp_path):
    from scripts.heo.voice_check import check
    from pathlib import Path
    draft = tmp_path / "draft.md"
    draft.write_text(GENERATED)
    fails = " ".join(check(draft).failures)
    assert "fragments" in fails and "single short line" in fails and "stock phrases" in fails
    # Two of his own posts, from 2009 and 2015, pass.
    for slug in ("taking-remote-imagery-offline-to-nigeria", "apple-watch-internet-of-humans"):
        (post,) = Path("content/_posts").glob(f"*-{slug}.html")
        assert check(post).failures == [], (post.name, check(post).failures)


def test_voice_check_blocks_tk_placeholders(tmp_path):
    from scripts.heo.voice_check import check
    p = tmp_path / "d.md"
    p.write_text(("Last week I was in Raleigh for the conference and talked with people about maps and data. " * 12)
                 + "\n\n[TK: who said it]\n")
    assert any("placeholder" in f for f in check(p).failures)


def test_wordpress_article_urls_have_a_post_or_redirect():
    """Every /articles/<slug>/ URL WordPress served maps to a post slug or a redirect."""
    import re as _re
    import yaml as _yaml
    root = Path(__file__).resolve().parent.parent
    urls = _yaml.safe_load((root / "_data/wordpress_urls.yml").read_text())["urls"]
    redirects = {r["from"] for r in _yaml.safe_load((root / "_data/redirects.yml").read_text())}
    slugs = set()
    for path in (root / "content/_posts").iterdir():
        front = _yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
        slugs.add(front.get("slug") or _re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem))
    sections = ("category/", "tag/")
    wanted = [u for u in urls if u.startswith("/articles/") and u != "/articles/" and not u[10:].startswith(sections)]
    assert wanted, "no article URLs listed"
    missing = [u for u in wanted if u[len("/articles/"):-1] not in slugs and u not in redirects]
    assert not missing, missing


def test_visibility_matches_shared_cases():
    """scripts/heo/content.visibility agrees with tests/visibility_cases.yml, the same
    cases _plugins/heo.rb is tested against in tests/visibility_test.rb."""
    import yaml as _yaml
    from scripts.heo.content import visibility
    spec = _yaml.safe_load((Path(__file__).parent / "visibility_cases.yml").read_text())
    d = spec["defaults"]
    for c in spec["cases"]:
        got = visibility(c["collection"], c["data"], staging=c["staging"],
                         excluded_albums=frozenset(str(x) for x in d["excluded_albums"]), user=d["user"])
        assert got == c["expect"], c["name"]


def _url_check(tmp_path, base, head, retired=None, existing=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    """Run scripts/ci/check_url_changes.py in a scratch repo layout."""
    import shutil
    root = Path(__file__).resolve().parent.parent
    (tmp_path / "_data").mkdir()
    if retired is not None:
        import yaml as _yaml
        (tmp_path / "_data/retired_urls.yml").write_text(_yaml.safe_dump(retired))
    for rel in existing:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    (tmp_path / "base.json").write_text(json.dumps(base))
    (tmp_path / "head.json").write_text(json.dumps(head))
    shutil.copy(root / "scripts/ci/check_url_changes.py", tmp_path / "check.py")
    import os, sys
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"}
    return subprocess.run([sys.executable, "check.py", "base.json", "head.json"], cwd=tmp_path,
                          capture_output=True, text=True, env=env)


def test_url_check_rules(tmp_path):
    post = "content/_posts/2020-01-01-a.md"
    # Unchanged and added URLs pass.
    r = _url_check(tmp_path / "1", {"/a/": post}, {"/a/": post, "/b/": None}, existing=[post])
    assert r.returncode == 0, r.stdout
    # A moved URL fails.
    r = _url_check(tmp_path / "2", {"/a/": post}, {"/a2/": post}, existing=[post])
    assert r.returncode == 1 and "now builds at /a2/" in r.stdout
    # A URL whose source still exists but builds nowhere (hidden) is a decision.
    r = _url_check(tmp_path / "3", {"/a/": post}, {}, existing=[post])
    assert r.returncode == 0 and "no longer built" in r.stdout
    # A deleted source fails unless the URL is retired.
    r = _url_check(tmp_path / "4", {"/a/": post}, {})
    assert r.returncode == 1 and "was removed" in r.stdout
    r = _url_check(tmp_path / "5", {"/a/": post}, {}, retired=[{"url": "/a/", "reason": "dup"}])
    assert r.returncode == 0
    # Generated pages only report.
    r = _url_check(tmp_path / "6", {"/articles/tag/x/": None}, {})
    assert r.returncode == 0
