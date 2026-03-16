import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "消息核查器 - AI Fact Checker",
  description: "通过多渠道验证消息准确性",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
