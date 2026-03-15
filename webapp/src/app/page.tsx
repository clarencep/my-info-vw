"use client";

import { useState } from "react";

interface CheckResult {
  level: string;
  type: string;
  message: string;
  report?: string;
}

export default function Home() {
  const [message, setMessage] = useState("");
  const [results, setResults] = useState<CheckResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCheck = async () => {
    if (!message.trim()) return;

    setLoading(true);
    setError("");
    setResults([]);

    try {
      const response = await fetch("/api/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error("核查请求失败");
      }

      const data = await response.json();
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setLoading(false);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case "SUCCESS":
        return "bg-green-100 border-green-500 text-green-800";
      case "WARNING":
        return "bg-yellow-100 border-yellow-500 text-yellow-800";
      case "ERROR":
        return "bg-red-100 border-red-500 text-red-800";
      default:
        return "bg-blue-100 border-blue-500 text-blue-800";
    }
  };

  const finalReport = results.find((r) => r.type === "complete");

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-4xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            🔍 消息核查器
          </h1>
          <p className="text-slate-500">
            AI 驱动的事实核查，通过多渠道验证消息准确性
          </p>
        </div>

        {/* Input Card */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="输入需要核查的消息..."
            className="w-full h-32 p-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-slate-700"
          />
          <div className="flex justify-between items-center mt-4">
            <span className="text-slate-400 text-sm">
              {message.length} 字符
            </span>
            <button
              onClick={handleCheck}
              disabled={loading || !message.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "核查中..." : "开始核查"}
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl mb-8">
            ❌ {error}
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-slate-700">核查过程</h2>
            {results.map((result, index) => (
              <div
                key={index}
                className={`border-l-4 px-4 py-3 rounded-r-xl ${getLevelColor(
                  result.level
                )}`}
              >
                <span className="text-xs font-bold uppercase">
                  {result.type}
                </span>
                <p className="mt-1">{result.message}</p>
              </div>
            ))}

            {/* Final Report */}
            {finalReport && finalReport.report && (
              <div className="mt-8 bg-white rounded-2xl shadow-lg p-6">
                <h2 className="text-xl font-semibold text-slate-700 mb-4">
                  📋 核查报告
                </h2>
                <div className="prose prose-slate max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-slate-600">
                    {finalReport.report}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
            <p className="mt-4 text-slate-500">AI 正在分析和验证...</p>
          </div>
        )}
      </div>
    </div>
  );
}
