import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import nodeProcess from "process";

export async function POST(request: Request) {
  try {
    const { message } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: "消息不能为空" },
        { status: 400 }
      );
    }

    // Get the project root (parent of webapp)
    const projectRoot = path.resolve(__dirname, "../../../..");
    const infoCheckScript = path.join(projectRoot, "info-check.py");

    // Run the CLI with --jsonl
    const result = await new Promise<string>((resolve, reject) => {
      const childProcess = spawn("uv", ["run", "python", infoCheckScript, message, "--jsonl"], {
        cwd: projectRoot,
        env: {
          ...nodeProcess.env,
        },
      });

      let output = "";
      let errorOutput = "";

      childProcess.stdout.on("data", (data) => {
        output += data.toString();
      });

      childProcess.stderr.on("data", (data) => {
        errorOutput += data.toString();
      });

      childProcess.on("close", (code) => {
        if (code === 0) {
          resolve(output);
        } else {
          reject(new Error(errorOutput || `Process exited with code ${code}`));
        }
      });

      childProcess.on("error", (err) => {
        reject(err);
      });
    });

    // Parse JSONL output
    const results = result
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return { level: "INFO", type: "parse", message: line };
        }
      });

    return NextResponse.json({ results });
  } catch (error) {
    console.error("Check error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "核查失败" },
      { status: 500 }
    );
  }
}
