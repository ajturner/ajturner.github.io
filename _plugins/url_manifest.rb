# When HEO_URL_MANIFEST names a file, write every URL this build produced to it as
# JSON: {"/url/": "content/_posts/file.html" or null for generated pages}. CI builds
# the base branch and the pull request this way, and scripts/ci/check_url_changes.py
# compares the two (see docs/site-contract.md, "URLs never disappear").

require "json"

Jekyll::Hooks.register :site, :post_write do |site|
  out = ENV["HEO_URL_MANIFEST"].to_s
  next if out.empty?
  urls = {}
  (site.pages + site.documents.select(&:write?)).each do |item|
    rel = item.relative_path.to_s
    source = File.file?(File.join(site.source, rel)) ? rel : nil
    urls[item.url] = source
  end
  File.write(out, JSON.pretty_generate(urls.sort.to_h))
  Jekyll.logger.info "URL manifest:", "#{urls.size} URLs written to #{out}"
end
