import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "SupportFlow AI",
  description:
    "Local demo for synthetic order lookup, policy drafts, and human review. Nothing is sent.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
