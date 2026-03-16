describe("Utility Functions", () => {
  it("basic test example", () => {
    const sum = (a: number, b: number) => a + b;
    expect(sum(2, 3)).toBe(5);
  });

  it("async test example", async () => {
    const asyncFunc = async () => {
      return new Promise((resolve) => {
        setTimeout(() => resolve("done"), 10);
      });
    };
    const result = await asyncFunc();
    expect(result).toBe("done");
  });
});
