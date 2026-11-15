# highearthorbit.com

Content and code for Andrew Turner's site. See README.md for how content, sync and publishing work.

## Writing

Any prose published as Andrew (posts, talk write-ups, project and album summaries, the About and Now pages) follows `docs/voice/style-guide.md`. Use the `heo-voice` skill (`.claude/skills/heo-voice/SKILL.md`) and check drafts with `python -m scripts.heo.voice_check <file>`. Never invent anecdotes, quotes or numbers; leave `[TK: …]` for Andrew to fill in.

## Site contract

`docs/site-contract.md` is the source of truth for URLs, slugs, visibility, redirects and feeds. A change that alters any of those must update that file in the same pull request, keep its checks passing, and never remove a URL without a redirect in `_data/redirects.yml` or an entry in `_data/retired_urls.yml`. Change the visibility rule only by adding a case to `tests/visibility_cases.yml` first and then updating both `_plugins/heo.rb` and `scripts/heo/content.py`.

## Checks before a pull request

```sh
python -m scripts.heo.validate
python -m pytest -q
ruby tests/visibility_test.rb
```
