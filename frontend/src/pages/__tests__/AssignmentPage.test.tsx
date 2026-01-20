import { render } from "@testing-library/react";
import { vi } from "vitest";

import AssignmentPage from "../AssignmentPage";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "1" }),
  Link: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const assignment = {
  assignment_id: 1,
  title: "Test Assignment",
  cpote: { problem_statement: "Problem" },
  milestones: [],
  groups: [],
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: assignment, isLoading: false, isError: false }),
}));

vi.mock("@/lib/api", () => ({
  assignmentsApi: { getById: vi.fn() },
}));

test("assignment page uses archive section class", () => {
  const { container } = render(<AssignmentPage />);
  expect(container.querySelector(".archive-section")).toBeTruthy();
});
