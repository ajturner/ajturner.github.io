# Runs HEO.visibility from _plugins/heo.rb against tests/visibility_cases.yml.
# CI: bundle exec ruby tests/visibility_test.rb. Works without Jekyll installed too,
# since only the plain functions in heo.rb are exercised.
require "minitest/autorun"
require "yaml"

unless defined?(Jekyll)
  module Jekyll
    class Generator
      def self.priority(*); end
      def self.safe(*); end
    end

    module Hooks
      def self.register(*); end
    end
  end
end

require_relative "../_plugins/heo"

class VisibilityCasesTest < Minitest::Test
  SPEC = YAML.safe_load(File.read(File.join(__dir__, "visibility_cases.yml")))

  SPEC["cases"].each_with_index do |c, i|
    define_method("test_#{i}_#{c["name"].gsub(/\W+/, "_")}") do
      d = SPEC["defaults"]
      got = HEO.visibility(c["collection"], c["data"], staging: c["staging"],
                           excluded_albums: d["excluded_albums"].map(&:to_s), user: d["user"])
      assert_equal c["expect"], got, c["name"]
    end
  end
end
