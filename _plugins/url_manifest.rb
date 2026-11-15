# When HEO_URL_MANIFEST names a file, write every URL this build produced to it as
# JSON: {"/url/": "content/_posts/file.html" or null for generated pages}. CI builds
# the base branch and the pull request this way, and scripts/ci/check_url_changes.py
# compares the two (see docs/site-contract.md, "URLs never disappear").

require "json"
require "pathname"

Jekyll::Hooks.register :site, :post_write do |site|
  out = ENV["HEO_URL_MANIFEST"].to_s
  next if out.empty?
  urls = {}
  root = Pathname.new(site.source)
  (site.pages + site.documents.select(&:write?)).each do |item|
    # A document's relative_path is relative to collections_dir (content/), so use
    # its absolute path; a page's is relative to the site source.
    abs = item.is_a?(Jekyll::Document) ? item.path : File.join(site.source, item.relative_path.to_s)
    urls[item.url] = File.file?(abs) ? Pathname.new(abs).relative_path_from(root).to_s : nil
  end
  File.write(out, JSON.pretty_generate(urls.sort.to_h))
  Jekyll.logger.info "URL manifest:", "#{urls.size} URLs written to #{out}"
end
