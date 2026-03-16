import { render } from "@testing-library/react";
import RootLayout from "../app/layout";

describe("Root Layout", () => {
  it("renders children correctly", () => {
    const { container } = render(
      <RootLayout>
        <div>Test Content</div>
      </RootLayout>
    );
    expect(container).toContainHTML("div");
  });

  it("sets correct lang attribute", () => {
    render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );
    const html = document.documentElement;
    expect(html).toHaveAttribute("lang", "zh-CN");
  });
});
