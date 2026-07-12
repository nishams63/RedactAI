import React from "react";
import Link from "next/link";
import { ShieldAlert, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-950 px-6 text-center">
      <div className="w-16 h-16 bg-brand-500/10 border border-brand-500/20 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-brand-500/10">
        <ShieldAlert className="w-8 h-8 text-brand-400" />
      </div>
      <h1 className="text-3xl font-bold text-white mb-2">
        Page Not Found
      </h1>
      <p className="text-surface-400 text-sm max-w-md mb-8 leading-relaxed">
        The requested resource path does not exist or has been locked under access-control guidelines. Check the target URL or return to dashboard.
      </p>
      <Link href="/dashboard" className="btn btn-brand flex items-center gap-2">
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>
    </div>
  );
}
