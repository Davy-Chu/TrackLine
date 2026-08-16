import { describe, expect, it } from "vitest";

import { environmentStatus } from "./health";

describe("development environment", () => {
  it("exports the frontend smoke status", () => {
    expect(environmentStatus).toBe("Frontend smoke check passed.");
  });
});
