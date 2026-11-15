require "cgi"


# Redirect pages for old URLs, from _data/redirects.yml. GitHub Pages cannot send HTTP
# redirects, so each old URL gets a page with a canonical link and an immediate
# meta refresh to the new one. Fails the build if a target page does not exist.

module HEO
  class Redirects < Jekyll::Generator
    safe true
    priority :lowest

    def generate(site)
      rules = Array(site.data["redirects"])
      return if rules.empty?
      base = site.config["baseurl"].to_s.chomp("/")
      urls = (site.pages + site.documents).map(&:url)
      rules.each do |rule|
        from, to = rule["from"].to_s, rule["to"].to_s
        raise "redirects.yml: #{from} must start and end with /" unless from.start_with?("/") && from.end_with?("/")
        raise "redirects.yml: #{from} points at #{to}, which this site does not build" unless urls.include?(to)
        page = Jekyll::PageWithoutAFile.new(site, site.source, from.delete_prefix("/").chomp("/"), "index.html")
        page.data["layout"] = nil
        page.data["sitemap"] = false
        title = CGI.escapeHTML(site.config["title"].to_s)
        # Root-relative hrefs get the base path from HEO.prefix_baseurl; the refresh
        # URL is in a content attribute, which that does not touch, so add it here.
        page.content = <<~HTML
          <!doctype html>
          <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Moved · #{title}</title>
            <meta name="robots" content="noindex">
            <link rel="canonical" href="#{site.config["url"]}#{to}">
            <meta http-equiv="refresh" content="0; url=#{base}#{to}">
          </head>
          <body><p>This page moved to <a href="#{to}">#{site.config["url"]}#{to}</a>.</p></body>
          </html>
        HTML
        site.pages << page
      end
    end
  end
end
