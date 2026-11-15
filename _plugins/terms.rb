# Category and tag pages at the WordPress URLs:
#
#   /articles/category/<slug>/   every post with that category
#   /articles/tag/<slug>/        every post with that tag
#   /articles/category/ and /articles/tag/   an index of each
#
# Slugs use Jekyll's default slugify, which matches WordPress for these names
# ("open data" -> open-data, "Where2.0" -> where2-0). Names that differ only in
# case or punctuation ("Neogeography", "neogeography") share one page, titled with
# the most used spelling. Runs after HEO::Visibility, so hidden posts are already
# dropped (or marked as drafts on staging).
#
# The WordPress URLs that must keep working are listed in _data/wordpress_urls.yml
# and checked against the build by scripts/ci/check_wordpress_urls.py.

module HEO
  class TermPages < Jekyll::Generator
    safe true
    priority :low

    KINDS = {
      "categories" => { path: "category", label: "Category", plural: "Categories" },
      "tags" => { path: "tag", label: "Tag", plural: "Tags" },
    }.freeze

    def generate(site)
      KINDS.each do |field, kind|
        terms = collect(site, field)
        terms.each_value do |term|
          site.pages << term_page(site, kind, term)
        end
        site.pages << index_page(site, kind, terms.values)
      end
    end

    private

    def collect(site, field)
      terms = {}
      site.posts.docs.each do |post|
        Array(post.data[field]).map(&:to_s).uniq.each do |name|
          slug = Jekyll::Utils.slugify(name)
          next if slug.empty?
          term = (terms[slug] ||= { "slug" => slug, "names" => Hash.new(0), "posts" => [] })
          term["names"][name] += 1
          term["posts"] << post unless term["posts"].include?(post)
        end
      end
      terms.each_value do |term|
        term["name"] = term["names"].max_by { |name, count| [count, name] }.first
        term["posts"].sort_by! { |p| p.date }.reverse!
      end
      terms
    end

    def term_page(site, kind, term)
      dir = "articles/#{kind[:path]}/#{term["slug"]}"
      page = Jekyll::PageWithoutAFile.new(site, site.source, dir, "index.html")
      page.data.merge!(
        "layout" => "term",
        "title" => term["name"],
        "term_kind" => kind[:label],
        "term_index" => "/articles/#{kind[:path]}/",
        "term_index_label" => "All #{kind[:plural].downcase}",
        "term_posts" => term["posts"],
        "summary" => "Writing on High Earth Orbit filed under #{term["name"]}."
      )
      page
    end

    def index_page(site, kind, terms)
      page = Jekyll::PageWithoutAFile.new(site, site.source, "articles/#{kind[:path]}", "index.html")
      page.data.merge!(
        "layout" => "term-index",
        "title" => kind[:plural],
        "term_list" => terms.sort_by { |t| t["name"].downcase }.map do |t|
          { "name" => t["name"], "url" => "/articles/#{kind[:path]}/#{t["slug"]}/", "count" => t["posts"].size }
        end
      )
      page
    end
  end
end
