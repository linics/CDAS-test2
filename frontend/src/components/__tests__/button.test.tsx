import { render } from "@testing-library/react";

import { Button } from "../ui/button";

test("button uses archive class", () => {
  const { container } = render(<Button>Action</Button>);
  const button = container.querySelector("button");
  expect(button?.className).toContain("archive-button");
});
