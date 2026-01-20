import { render } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("../contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    logout: vi.fn(),
  }),
}));

import App from "../App";

test("app root renders with archive ui class", () => {
  render(<App />);
  expect(document.body.classList.contains("archive-ui")).toBe(true);
});
