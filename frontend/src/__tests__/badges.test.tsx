import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskBadge, ResultChip, ActionBadge } from "../components/ui";

describe("RiskBadge", () => {
  it("shows risk level text", () => {
    render(<RiskBadge risk="high" />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("falls back for unknown risks", () => {
    render(<RiskBadge risk="weird" />);
    expect(screen.getByText("weird")).toBeInTheDocument();
  });
});

describe("ResultChip", () => {
  it("renders pass/fail/flag", () => {
    render(<ResultChip result="fail" />);
    expect(screen.getByText("fail")).toBeInTheDocument();
    render(<ResultChip result="flag" />);
    expect(screen.getByText("flag")).toBeInTheDocument();
    render(<ResultChip result="pass" />);
    expect(screen.getByText("pass")).toBeInTheDocument();
  });
});

describe("ActionBadge", () => {
  it("renders nothing when no action", () => {
    render(<ActionBadge action={null} />);
    expect(document.body.textContent).toBe("");
  });

  it("labels the qualify action", () => {
    render(<ActionBadge action="qualify" />);
    expect(screen.getByText("Recommend: Qualify")).toBeInTheDocument();
  });
});