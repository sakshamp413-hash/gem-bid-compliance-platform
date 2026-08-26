import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ScoreGauge from "../components/ScoreGauge";

describe("ScoreGauge", () => {
  it("renders the numeric score", () => {
    render(<ScoreGauge score={94.8} />);
    expect(screen.getByText("94.8")).toBeInTheDocument();
  });

  it("renders the scale label", () => {
    render(<ScoreGauge score={50} />);
    expect(screen.getByText("out of 100")).toBeInTheDocument();
  });
});