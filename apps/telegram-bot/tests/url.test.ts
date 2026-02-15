import { describe, expect, it } from "vitest";

import { extractUrls } from "../src/application/url";

describe("extractUrls", () => {
  it("extracts one url", () => {
    expect(extractUrls("check https://example.com now")).toEqual(["https://example.com"]);
  });

  it("extracts unique urls only", () => {
    expect(
      extractUrls("https://example.com a https://example.com b https://test.dev/path?q=1")
    ).toEqual(["https://example.com", "https://test.dev/path?q=1"]);
  });

  it("returns empty list when no urls", () => {
    expect(extractUrls("plain text")).toEqual([]);
  });
});
