import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders a human-readable label, not just a colour", () => {
    render(<StatusBadge status="in_review" />);
    expect(screen.getByText("in review")).toBeInTheDocument();
  });
});
