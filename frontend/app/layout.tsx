import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/providers/Providers";

export const metadata: Metadata = {
  title: "RedactAI — AI-Powered Legal Document Privacy Platform",
  description:
    "Enterprise-grade AI platform for legal document privacy, PII detection, and compliance management. Built for India's legal and regulatory landscape.",
  keywords: ["legal", "document", "privacy", "redaction", "compliance", "AI", "India"],
  icons: {
    icon: "/favicon.ico",
  },
  openGraph: {
    title: "RedactAI — AI-Powered Legal Document Privacy Platform",
    description: "Enterprise-grade AI platform for automated PII detection, document redaction, and compliance management.",
    url: "https://redactai.in",
    siteName: "RedactAI",
    locale: "en_IN",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
