"use client";

import React from "react";
import { Shield } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-950 text-white">
      <div className="relative flex items-center justify-center mb-4">
        <div className="w-16 h-16 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
        <Shield className="w-6 h-6 text-brand-400 absolute" />
      </div>
      <p className="text-surface-300 text-sm font-medium animate-pulse">
        Securing document workspace...
      </p>
    </div>
  );
}
