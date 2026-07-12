"use client";

import React, { useEffect } from "react";
import { ShieldAlert, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Next.js Error boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-950 px-6 text-center">
      <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-red-500/10 animate-bounce-slow">
        <ShieldAlert className="w-8 h-8 text-red-500" />
      </div>
      <h1 className="text-2xl font-bold text-white mb-2">
        An unexpected security error occurred
      </h1>
      <p className="text-surface-400 text-sm max-w-md mb-8 leading-relaxed">
        The workspace boundary encountered an unhandled exception. Verify network status or reload session credentials to resolve.
      </p>
      <button
        onClick={() => reset()}
        className="btn btn-brand flex items-center gap-2"
      >
        <RefreshCw className="w-4 h-4" />
        Retry Operation
      </button>
    </div>
  );
}
