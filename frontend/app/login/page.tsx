"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { Shield, Eye, EyeOff, ArrowRight, UserPlus } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden" style={{ background: '#090B12' }}>
      {/* ── Cinematic Background ─────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Ambient light orbs */}
        <div className="absolute top-[-20%] left-[-10%] w-[700px] h-[700px] rounded-full animate-glow"
             style={{ background: 'radial-gradient(circle, rgba(79,124,255,0.15) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full animate-glow"
             style={{ background: 'radial-gradient(circle, rgba(0,225,199,0.1) 0%, transparent 70%)', animationDelay: '2s' }} />
        <div className="absolute top-[40%] left-[60%] w-[400px] h-[400px] rounded-full animate-pulse-soft"
             style={{ background: 'radial-gradient(circle, rgba(215,255,126,0.05) 0%, transparent 70%)', animationDelay: '1s' }} />

        {/* Subtle grid */}
        <div className="absolute inset-0 opacity-[0.02]"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '64px 64px' }} />

        {/* Floating geometric elements */}
        <div className="absolute top-[15%] right-[20%] w-32 h-32 border border-brand-500/10 rounded-3xl rotate-12 animate-float" />
        <div className="absolute bottom-[25%] left-[15%] w-24 h-24 border border-accent-teal/10 rounded-2xl -rotate-6 animate-float" style={{ animationDelay: '3s' }} />
        <div className="absolute top-[60%] right-[35%] w-16 h-16 border border-accent-lime/10 rounded-xl rotate-45 animate-float" style={{ animationDelay: '1.5s' }} />
      </div>

      {/* ── Left: Cinematic Hero ─────────────────────────── */}
      <div className="hidden lg:flex lg:w-[55%] relative items-center justify-center p-16">
        <div className="relative z-10 max-w-xl">
          {/* Brand */}
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center border-glow"
                 style={{ background: 'linear-gradient(135deg, rgba(79,124,255,0.15), rgba(0,225,199,0.1))', border: '1px solid rgba(79,124,255,0.2)' }}>
              <Shield className="w-6 h-6 text-brand-500" />
            </div>
            <span className="text-2xl font-display font-bold tracking-tight">
              Redact<span className="gradient-text-ai">AI</span>
            </span>
          </div>

          {/* Hero typography */}
          <h1 className="text-display text-6xl mb-6 leading-[1.05]">
            AI Document<br />
            <span className="gradient-text-ai">Intelligence</span>
          </h1>

          <p className="text-lg text-[#AEB6C4] max-w-md leading-relaxed mb-14 font-light">
            Enterprise-grade platform for automated PII detection, document redaction, and compliance management. Built for India&apos;s regulatory landscape.
          </p>

          {/* Feature pills */}
          <div className="flex flex-col gap-5">
            {[
              { label: "Automated PII Detection", color: "#4F7CFF" },
              { label: "DPDP Act Compliance", color: "#00E1C7" },
              { label: "Enterprise RBAC", color: "#D7FF7E" }
            ].map((feature, i) => (
              <div key={i} className="flex items-center gap-4 group">
                <div className="w-1.5 h-1.5 rounded-full transition-all duration-300 group-hover:scale-150 group-hover:shadow-[0_0_12px_currentColor]"
                     style={{ backgroundColor: feature.color }} />
                <span className="text-sm font-medium text-[#AEB6C4] tracking-wide group-hover:text-white transition-colors duration-300">
                  {feature.label}
                </span>
              </div>
            ))}
          </div>

          {/* Floating document hologram */}
          <div className="absolute -right-8 top-[20%] w-64 h-80 animate-float" style={{ animationDelay: '0.5s' }}>
            <div className="relative w-full h-full rounded-2xl overflow-hidden"
                 style={{ background: 'linear-gradient(135deg, rgba(79,124,255,0.08), rgba(0,225,199,0.05))', border: '1px solid rgba(79,124,255,0.12)' }}>
              {/* Scan line */}
              <div className="absolute inset-x-0 h-px animate-scan"
                   style={{ background: 'linear-gradient(90deg, transparent, rgba(79,124,255,0.6), transparent)' }} />
              {/* Fake document lines */}
              <div className="p-6 space-y-3">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="h-1.5 rounded-full"
                       style={{
                         width: `${60 + Math.random() * 35}%`,
                         background: `rgba(255,255,255,${0.03 + Math.random() * 0.04})`,
                       }} />
                ))}
                <div className="mt-6 space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={`r-${i}`} className="h-3 rounded"
                         style={{
                           width: `${30 + Math.random() * 40}%`,
                           background: 'rgba(255,92,122,0.15)',
                           border: '1px solid rgba(255,92,122,0.1)',
                         }} />
                  ))}
                </div>
              </div>
              {/* Shield overlay */}
              <div className="absolute bottom-4 right-4 w-8 h-8 rounded-lg flex items-center justify-center"
                   style={{ background: 'rgba(79,124,255,0.1)', border: '1px solid rgba(79,124,255,0.15)' }}>
                <Shield className="w-4 h-4 text-brand-500/60" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right: Login Form ────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 sm:px-8 py-12 relative z-10">
        <div className="w-full max-w-[420px] animate-fade-in">
          {/* Mobile Logo */}
          <div className="flex items-center gap-3 mb-10 lg:hidden">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'linear-gradient(135deg, rgba(79,124,255,0.15), rgba(0,225,199,0.1))', border: '1px solid rgba(79,124,255,0.2)' }}>
              <Shield className="w-5 h-5 text-brand-500" />
            </div>
            <span className="text-xl font-display font-bold tracking-tight">
              Redact<span className="gradient-text-ai">AI</span>
            </span>
          </div>

          {/* Heading */}
          <div className="mb-10">
            <h2 className="text-display text-4xl mb-3">Welcome back</h2>
            <p className="text-[#AEB6C4] text-base font-light">Sign in to your account to continue</p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 p-4 rounded-2xl text-sm font-medium animate-slide-up"
                 style={{ background: 'rgba(255,92,122,0.08)', border: '1px solid rgba(255,92,122,0.15)', color: '#FF5C7A' }}>
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold mb-2.5 text-[#AEB6C4] uppercase tracking-widest">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                placeholder="you@company.com"
                required
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-semibold mb-2.5 text-[#AEB6C4] uppercase tracking-widest">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pr-12"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#AEB6C4]/50 hover:text-white transition-colors duration-200"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary w-full mt-2">
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-10 text-center">
            <p className="text-[#AEB6C4]/60 text-sm">
              Don&apos;t have an account?{" "}
              <button
                onClick={() => router.push("/register")}
                className="text-brand-500 hover:text-brand-400 font-semibold transition-colors duration-200 inline-flex items-center gap-1.5"
              >
                Create Account <UserPlus className="w-3.5 h-3.5" />
              </button>
            </p>
          </div>

          {/* Trust indicators */}
          <div className="mt-12 flex items-center justify-center gap-6">
            {["SOC 2", "DPDP", "ISO 27001"].map((cert, i) => (
              <span key={i} className="text-[10px] font-bold tracking-[0.15em] uppercase px-3 py-1.5 rounded-full"
                    style={{ color: 'rgba(174,182,196,0.35)', border: '1px solid rgba(255,255,255,0.04)' }}>
                {cert}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
