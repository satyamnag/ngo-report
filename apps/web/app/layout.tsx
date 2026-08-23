import type { Metadata } from "next";
import ErrorBoundary from "@/components/ErrorBoundary";
import "./globals.css";

export const metadata: Metadata = {
  title: "NGO Report Studio",
  description: "Generate, edit and export NGO annual reports from templates",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}