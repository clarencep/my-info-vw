import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Home Page", () => {
  it("renders without crashing", () => {
    render(<Home />);
  });

  it("displays the main heading", () => {
    render(<Home />);
    const heading = screen.getByText(/🔍 消息核查器/);
    expect(heading).toBeInTheDocument();
  });

  it("displays the description", () => {
    render(<Home />);
    const description = screen.getByText(/AI 驱动的事实核查/);
    expect(description).toBeInTheDocument();
  });

  it("has a textarea for message input", () => {
    render(<Home />);
    const textarea = screen.getByPlaceholderText(/输入需要核查的消息/);
    expect(textarea).toBeInTheDocument();
  });

  it("has a disabled button initially", () => {
    render(<Home />);
    const button = screen.getByRole("button", { name: /开始核查/ });
    expect(button).toBeDisabled();
  });

  it("shows character count", () => {
    render(<Home />);
    const charCount = screen.getByText(/0 字符/);
    expect(charCount).toBeInTheDocument();
  });
});
