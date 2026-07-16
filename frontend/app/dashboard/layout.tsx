"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { useTheme } from "next-themes";
import {
  Shield, LayoutDashboard, FileText, Building2, User, LogOut,
  Menu, X, Sun, Moon, ChevronDown, Bell, Brain, CheckSquare, Cpu, ShieldCheck,
  MessageSquare, Bookmark, Network, Activity
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Documents", href: "/dashboard/documents", icon: FileText },
  { label: "ML Analytics", href: "/dashboard/ml", icon: Brain },
  { label: "DL Analytics", href: "/dashboard/dl", icon: Brain },
  { label: "Legal AI", href: "/dashboard/legal-ai", icon: Shield },
  { label: "AI Copilot", href: "/dashboard/copilot", icon: MessageSquare },
  { label: "AI Workspace", href: "/dashboard/workspace", icon: Bookmark },
  { label: "Knowledge Graph", href: "/dashboard/graph", icon: Network },
  { label: "Agent Monitor", href: "/dashboard/agents", icon: Activity },
  { label: "Security", href: "/dashboard/security", icon: Shield },
  { label: "AI Quality", href: "/dashboard/ai-quality", icon: CheckSquare },
  { label: "Validation", href: "/dashboard/validation", icon: CheckSquare },
  { label: "Performance", href: "/dashboard/performance", icon: Cpu },
  { label: "Release", href: "/dashboard/release", icon: ShieldCheck },
  { label: "Organizations", href: "/dashboard/organizations", icon: Building2 },
  { label: "Profile", href: "/dashboard/profile", icon: User },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#090B12' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
          <p className="text-[#AEB6C4]/50 text-xs font-medium tracking-wider uppercase">Loading</p>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex" style={{ background: '#090B12' }}>
      {/* Sidebar Overlay (Mobile) */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-[272px]
                     flex flex-col transition-transform duration-300 ease-out
                     ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
        style={{
          background: 'rgba(18, 24, 38, 0.6)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 h-[72px]" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                 style={{ background: 'linear-gradient(135deg, rgba(79,124,255,0.15), rgba(0,225,199,0.1))', border: '1px solid rgba(79,124,255,0.15)' }}>
              <Shield className="w-[18px] h-[18px] text-brand-500" />
            </div>
            <span className="text-lg font-display font-bold tracking-tight">
              Redact<span className="gradient-text-ai">AI</span>
            </span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-[#AEB6C4]/50 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-5 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <button
                key={item.href}
                onClick={() => { router.push(item.href); setSidebarOpen(false); }}
                className={`w-full ${isActive ? "sidebar-link-active" : "sidebar-link"}`}
              >
                <item.icon className="w-[18px] h-[18px]" style={{ opacity: isActive ? 1 : 0.6 }} />
                <span>{item.label}</span>
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-500" style={{ boxShadow: '0 0 8px rgba(79,124,255,0.6)' }} />
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="px-4 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors hover:bg-white/[0.03]">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-semibold text-xs"
                 style={{ background: 'linear-gradient(135deg, #4F7CFF, #00E1C7)' }}>
              {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user?.full_name}</p>
              <p className="text-[10px] text-[#AEB6C4]/50 truncate uppercase tracking-wider font-medium">{user?.roles?.[0] || "User"}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-[72px] flex items-center justify-between px-6 lg:px-8 sticky top-0 z-30"
                style={{ background: 'rgba(9, 11, 18, 0.8)', backdropFilter: 'blur(16px)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-[#AEB6C4]/50 hover:text-white transition-colors">
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-base font-display font-semibold tracking-tight hidden sm:block">
                {navItems.find((item) => item.href === pathname)?.label || "RedactAI"}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#AEB6C4]/40 hover:text-white hover:bg-white/[0.04] transition-all duration-200"
            >
              {theme === "dark" ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
            </button>

            {/* Notifications */}
            <button className="w-9 h-9 rounded-xl flex items-center justify-center text-[#AEB6C4]/40 hover:text-white hover:bg-white/[0.04] transition-all duration-200 relative">
              <Bell className="w-[18px] h-[18px]" />
              <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full"
                    style={{ background: '#4F7CFF', boxShadow: '0 0 8px rgba(79,124,255,0.6)' }} />
            </button>

            {/* Separator */}
            <div className="w-px h-6 mx-1" style={{ background: 'rgba(255,255,255,0.06)' }} />

            {/* Profile Menu */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-white/[0.04] transition-all duration-200"
              >
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white font-semibold text-[11px]"
                     style={{ background: 'linear-gradient(135deg, #4F7CFF, #00E1C7)' }}>
                  {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-[#AEB6C4]/40" />
              </button>

              {profileOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
                  <div className="absolute right-0 mt-2 w-56 glass-card py-1.5 z-50 animate-slide-up"
                       style={{ borderRadius: '16px' }}>
                    <div className="px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <p className="text-sm font-semibold truncate">{user?.full_name}</p>
                      <p className="text-xs text-[#AEB6C4]/50 truncate mt-0.5">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => { router.push("/dashboard/profile"); setProfileOpen(false); }}
                      className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/[0.04] flex items-center gap-3 transition-colors text-[#AEB6C4] hover:text-white"
                    >
                      <User className="w-4 h-4" /> Profile
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full px-4 py-2.5 text-left text-sm flex items-center gap-3 transition-colors"
                      style={{ color: '#FF5C7A' }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,92,122,0.06)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <LogOut className="w-4 h-4" /> Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 px-6 lg:px-8 py-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
