import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    login: vi.fn(),
  }),
}));

import LoginPage from "../LoginPage";

test("login page uses archive cover class", () => {
  const { container } = render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
  expect(container.querySelector(".archive-cover")).toBeTruthy();
});
