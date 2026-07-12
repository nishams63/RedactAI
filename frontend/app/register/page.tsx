"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { Shield, Eye, EyeOff, ArrowRight, LogIn } from "lucide-react";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await register({
        email,
        password,
        full_name: fullName,
        organization_name: orgName || undefined,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-surface-900 via-brand-950 to-indigo-950">
        <div className="absolute inset-0">
          <div className="absolute top-20 left-20 w-72 h-72 bg-brand-500/20 rounded-full blur-3xl animate-pulse-soft" />
          <div className="absolute bottom-32 right-16 w-96 h-96 bg-indigo-500/15 rounded-full blur-3xl animate-pulse-soft" style={{ animationDelay: "1s" }} />
        </div>
        <div className="relative z-10 flex flex-col justify-center px-16">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-brand-500/30">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <span className="text-3xl font-bold text-white">
              Redact<span className="text-brand-400">AI</span>
            </span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4 leading-tight">
            Get Started with<br />RedactAI Today
          </h1>
          <p className="text-lg text-surface-300 max-w-md leading-relaxed">
            Create your account to start protecting sensitive information in legal documents with AI-powered automation.
          </p>
        </div>
      </div>

      {/* Right Panel — Register Form */}
      <div className="flex-1 flex items-center justify-center px-8 py-12">
        <div className="w-full max-w-md animate-fade-in">
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-10 h-10 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold">
              Redact<span className="gradient-text">AI</span>
            </span>
          </div>

          <h2 className="text-3xl font-bold mb-2">Create Account</h2>
          <p className="text-[rgb(var(--text-secondary))] mb-8">Join RedactAI to protect your legal documents</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-sm font-medium animate-slide-up">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-sm font-semibold mb-2">Full Name</label>
              <input id="fullName" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                className="input-field" placeholder="Your full name" required />
            </div>
            <div>
              <label htmlFor="regEmail" className="block text-sm font-semibold mb-2">Email Address</label>
              <input id="regEmail" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                className="input-field" placeholder="you@company.com" required />
            </div>
            <div>
              <label htmlFor="regPassword" className="block text-sm font-semibold mb-2">Password</label>
              <div className="relative">
                <input id="regPassword" type={showPassword ? "text" : "password"} value={password}
                  onChange={(e) => setPassword(e.target.value)} className="input-field pr-12"
                  placeholder="Min. 8 characters" required minLength={8} />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))] transition-colors">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="orgName" className="block text-sm font-semibold mb-2">Organization Name <span className="text-[rgb(var(--text-secondary))] font-normal">(optional)</span></label>
              <input id="orgName" type="text" value={orgName} onChange={(e) => setOrgName(e.target.value)}
                className="input-field" placeholder="Your company name" />
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary w-full mt-2">
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>Create Account <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-[rgb(var(--text-secondary))] text-sm">
              Already have an account?{" "}
              <button onClick={() => router.push("/login")}
                className="text-brand-500 hover:text-brand-400 font-semibold transition-colors inline-flex items-center gap-1">
                Sign In <LogIn className="w-3.5 h-3.5" />
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
