import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the title as a status role for screen readers", () => {
    render(<EmptyState title="No products have been published yet." />);
    expect(screen.getByRole("status")).toHaveTextContent("No products have been published yet.");
  });
});
