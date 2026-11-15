# Site contract

What highearthorbit.com promises, independent of the tool that builds it. Jekyll implements it today; any replacement (another static generator, a CMS) must keep every rule here, and the checks listed make that testable. When a change alters one of these rules, update this file in the same pull request.

Each rule names where it is implemented and what enforces it. A rule with no check says so.

## 1. Content model

- **One file per item.** Every article, outside article, talk, project and photo album is one Markdown or HTML file with YAML front matter under `content/` (`_posts`, `_external`, `_talks`, `_projects`, `_photos`).
  *Checked by:* `python -m scripts.heo.validate` against `schemas/*.schema.json`, which reject unknown fields.
- **`source_id` never changes.** It is the identity used by the sync jobs and the WordPress publisher.
  *Checked by:* nothing automatic. Review.
- **Curated and synced fields are separate.** Sync jobs only write the `synced:` block. Everything else is curated by hand, except posts whose `source_id` starts with `notion:`, which the Notion sync rewrites in full.
  *Checked by:* `scripts/heo/only_synced.py`, which decides whether a sync pull request may auto-merge.

## 2. URLs

### Patterns

| Item | URL |
| --- | --- |
| Home | `/` |
| Article | `/articles/<slug>/` |
| Outside article record | `/articles/elsewhere/<file name>/` |
| Talk | `/talks/<file name>/` |
| Project | `/projects/<file name>/` |
| Photo album | `/photos/<file name>/` |
| Category, tag | `/articles/category/<term slug>/`, `/articles/tag/<term slug>/` |
| Category and tag indexes | `/articles/category/`, `/articles/tag/` |
| Section pages | `/articles/`, `/projects/`, `/talks/`, `/photos/`, `/about/`, `/now/` |
| Feeds | `/feed.xml` (writing), `/talks/feed.xml`, `/projects/feed.xml` |
| Old feed address | `/feed/` points readers to `/feed.xml` |

*Implemented in:* `_config.yml` (`permalink`, `collections`), `_plugins/terms.rb`, `feed/index.html`.

### Slugs

- **Article slug.** The `slug` field when present, otherwise the file name without its `YYYY-MM-DD-` prefix and extension. A post whose file name differs from its WordPress slug carries a `slug:` line.
- **Term slug.** Lowercase the name, replace each run of characters that are not letters, marks or digits with one hyphen, and trim hyphens from both ends. "open data" becomes `open-data` and "Where2.0" becomes `where2-0`. This is Jekyll's default `slugify`, which matches WordPress for every term in use. Names that slug the same ("Neogeography", "neogeography") share one page, titled with the most used spelling.
- **File names are URLs.** Renaming a talk, project or album file changes its URL.

*Checked by:* `tests/test_heo.py::test_wordpress_article_urls_have_a_post_or_redirect` for the WordPress-era article slugs, and the URL check below for everything else.

### URLs never disappear

A URL that a build has published stays reachable. Between the base branch and a pull request, a URL may go away only when one of these is true:

1. **Visibility decision.** Its source file still exists but is no longer built: hidden, its repository lost the `portfolio` topic, or its album was excluded.
2. **Redirect.** The old URL is listed in `_data/redirects.yml` and so gets a redirect page.
3. **Retirement.** Its source file was deleted and the URL is listed in `_data/retired_urls.yml` with a reason.

A generated page such as a tag page may also go away when nothing produces it any more.

*Checked by:* CI builds both branches with `_plugins/url_manifest.rb` and runs `scripts/ci/check_url_changes.py`. A URL that moved, or whose source was deleted without a redirect or retirement, fails the pull request.

- **WordPress URLs.** Every URL the WordPress site listed in its sitemap on November 15, 2026 resolves, apart from five placeholder pages named in the file.
  *Checked by:* `scripts/ci/check_wordpress_urls.py` against `_data/wordpress_urls.yml`, on every build.

### Redirects

- Static hosting cannot send HTTP redirects, so each redirect is a page with a `canonical` link and an immediate `meta refresh` to the new URL, marked `noindex`.
- A redirect whose target is not built fails the build.

*Implemented in:* `_plugins/redirects.rb`, from `_data/redirects.yml`.

## 3. Visibility

| Item | Public site | Staging |
| --- | --- | --- |
| Not hidden | Shown | Shown |
| `hidden: true` (articles, talks, projects) | Not built | Built with a Draft badge |
| Photo album that is hidden or listed in `_data/flickr_exclude.yml` | Not built | Not built |
| Project from one of Andrew's own repositories without the `portfolio` topic | Not built | Not built |
| Project from another owner, or with no repository | Shown | Shown |

`hidden` counts only when it is literally `true`. Album exclusion is about privacy, so it applies on staging too. The `portfolio` rule takes priority over `hidden`.

*Implemented twice:* `_plugins/heo.rb` (`HEO.visibility`, for the site) and `scripts/heo/content.py` (`visibility`, for the publisher).
*Checked by:* both implementations run against the same cases in `tests/visibility_cases.yml`: `tests/visibility_test.rb` and `tests/test_heo.py::test_visibility_matches_shared_cases`. Add a case there before changing the rule.

## 4. Builds

- **Staging.** With `heo.staging: true`, drafts are shown, every page carries `noindex, nofollow`, and a banner names the live site.
  *Implemented in:* `_config.yml`, `_layouts/default.html`.
- **Base path.** Templates write root-relative paths (`/assets/...`) and never `relative_url`. When the site is served under a base path, root-relative `href`, `src`, `srcset` and `poster` attributes are rewritten at build time. Content outside those attributes, such as a `meta refresh`, must add the base path itself.
  *Implemented in:* `_plugins/heo.rb` (`HEO.prefix_baseurl`).
  *Checked by:* `scripts/ci/check_links.py`, which builds under the repository's base path and fails on internal links that don't resolve.
- **Internal links resolve.** Every internal link and image in the built site points at a file, apart from links into the 2004 to 2017 archive that were already broken, which are warnings.
  *Checked by:* `scripts/ci/check_links.py`.

## 5. Writing

Prose published as Andrew follows `docs/voice/style-guide.md`.
*Checked by:* `python -m scripts.heo.voice_check FILE`, and the Notion sync holds back any page with a `[TK: …]` placeholder.

## Moving to another tool

A replacement for Jekyll is done when:

1. It reads the same `content/` files and `_data/` lists, or a lossless conversion of them.
2. It produces every URL in a URL manifest taken from the last Jekyll build, or redirects it.
3. It passes `scripts/ci/check_wordpress_urls.py` and `scripts/ci/check_links.py` against its output.
4. Its visibility rule passes `tests/visibility_cases.yml`.
5. It writes the three feeds at the same addresses.

## Checks at a glance

| Rule | Check | Runs |
| --- | --- | --- |
| Front matter fields | `scripts/heo/validate.py` | CI validate job |
| Visibility, both implementations | `tests/visibility_cases.yml` | CI validate and build jobs |
| WordPress-era article slugs | `tests/test_heo.py` | CI validate job |
| WordPress URLs resolve | `scripts/ci/check_wordpress_urls.py` | CI build job |
| No URL disappears | `scripts/ci/check_url_changes.py` | CI build job, pull requests |
| Internal links resolve | `scripts/ci/check_links.py` | CI build job |
| Sync pull requests only touch synced data | `scripts/heo/only_synced.py` | Weekly sync |
| Voice | `scripts/heo/voice_check.py` | By hand, and the Notion sync |
