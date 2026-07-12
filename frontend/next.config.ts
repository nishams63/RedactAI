import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.VERCEL !== "1" ? { output: "standalone" } : {}),
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "9000",
      },
      {
        protocol: "https",
        hostname: "*.amazonaws.com",
      },
    ],
  },
};

export default nextConfig;
