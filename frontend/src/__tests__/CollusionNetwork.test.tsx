import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { CollusionNetwork, GraphData } from "../components/CollusionNetwork";

const mockGraphData: GraphData = {
  nodes: [
    { id: "s1", label: "Alpha Tech Ltd", submission_id: 1, group: 0, suspicious: false },
    { id: "s2", label: "Beta Solutions", submission_id: 2, group: 1, suspicious: true },
    { id: "s3", label: "Gamma Systems", submission_id: 3, group: 1, suspicious: true },
  ],
  links: [
    {
      source: "s2",
      target: "s3",
      value: 0.99,
      attributes: [{ attribute: "pan", value: "ABCDE1234F", match: "exact", confidence: 0.99 }],
      match_type: "exact",
    },
  ],
  metadata: {
    tender_id: 1,
    node_count: 3,
    link_count: 1,
    cluster_count: 1,
    risk_level: "high",
    source: "● MOCK (offline deterministic)",
  },
};

describe("CollusionNetwork", () => {
  it("renders header with risk badge and counts", () => {
    render(<CollusionNetwork data={mockGraphData} width={500} height={300} />);
    expect(screen.getByText(/Procurement Integrity Graph/i)).toBeInTheDocument();
    expect(screen.getByText(/3 bidders · 1 links · 1 collusion clusters/i)).toBeInTheDocument();
    expect(screen.getByText(/HIGH RISK/i)).toBeInTheDocument();
  });

  it("renders node labels in the SVG canvas", () => {
    render(<CollusionNetwork data={mockGraphData} width={500} height={300} />);
    expect(screen.getByText(/Alpha Tech/i)).toBeInTheDocument();
    expect(screen.getByText(/Beta Solutions/i)).toBeInTheDocument();
  });

  it("renders legend with match type details", () => {
    render(<CollusionNetwork data={mockGraphData} width={500} height={300} />);
    expect(screen.getByText(/Independent Bidder/i)).toBeInTheDocument();
    expect(screen.getByText(/Collusion Ring/i)).toBeInTheDocument();
    expect(screen.getByText(/Exact Shared Identifier/i)).toBeInTheDocument();
  });
});
