"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { useTheme } from "next-themes";
import {
  Shield, LayoutDashboard, FileText, Building2, User, LogOut,
  Menu, X, Sun, Moon, ChevronDown, Bell, Brain, CheckSquare, Cpu, ShieldCheck
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Documents", href: "/dashboard/documents", icon: FileText },
  { label: "ML Analytics", href: "/dashboard/ml", icon: Brain },
  { label: "DL Analytics", href: "/dashboard/dl", icon: Brain },
  { label: "Legal AI", href: "/dashboard/legal-ai", icon: Shield },
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex bg-[rgb(var(--bg-primary))]">
      {/* Sidebar Overlay (Mobile) */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-72 
                     bg-[rgb(var(--bg-card))] border-r border-[rgb(var(--border-color))]/50 
                     flex flex-col transition-transform duration-300 
                     ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[rgb(var(--border-color))]/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-brand-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold">
              Redact<span className="gradient-text">AI</span>
            </span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-[rgb(var(--text-secondary))]">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <button
                key={item.href}
                onClick={() => { router.push(item.href); setSidebarOpen(false); }}
                className={isActive ? "sidebar-link-active w-full" : "sidebar-link w-full"}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="px-4 py-4 border-t border-[rgb(var(--border-color))]/50">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-9 h-9 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-full flex items-center justify-center text-white font-semibold text-sm">
              {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user?.full_name}</p>
              <p className="text-xs text-[rgb(var(--text-secondary))] truncate">{user?.roles?.[0] || "User"}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="h-16 bg-[rgb(var(--bg-card))]/80 backdrop-blur-xl border-b border-[rgb(var(--border-color))]/50 flex items-center justify-between px-6 sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-[rgb(var(--text-secondary))]">
              <Menu className="w-6 h-6" />
            </button>
            <h1 className="text-lg font-semibold hidden sm:block">
              {navItems.find((item) => item.href === pathname)?.label || "RedactAI"}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="w-10 h-10 rounded-xl bg-[rgb(var(--bg-secondary))] flex items-center justify-center 
                         text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))] 
                         hover:bg-[rgb(var(--border-color))]/50 transition-all duration-200"
            >
              {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {/* Notifications Placeholder */}
            <button className="w-10 h-10 rounded-xl bg-[rgb(var(--bg-secondary))] flex items-center justify-center 
                               text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--text-primary))] 
                               hover:bg-[rgb(var(--border-color))]/50 transition-all duration-200 relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-brand-500 rounded-full" />
            </button>

            {/* Profile Menu */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-[rgb(var(--bg-secondary))] transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-full flex items-center justify-center text-white font-semibold text-xs">
                  {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
                </div>
                <ChevronDown className="w-4 h-4 text-[rgb(var(--text-secondary))]" />
              </button>

              {profileOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
                  <div className="absolute right-0 mt-2 w-56 glass-card py-2 z-50 animate-slide-up">
                    <div className="px-4 py-3 border-b border-[rgb(var(--border-color))]/50">
                      <p className="text-sm font-semibold truncate">{user?.full_name}</p>
                      <p className="text-xs text-[rgb(var(--text-secondary))] truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => { router.push("/dashboard/profile"); setProfileOpen(false); }}
                      className="w-full px-4 py-2.5 text-left text-sm hover:bg-[rgb(var(--bg-secondary))] flex items-center gap-3 transition-colors"
                    >
                      <User className="w-4 h-4" /> Profile
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full px-4 py-2.5 text-left text-sm text-red-500 hover:bg-red-500/10 flex items-center gap-3 transition-colors"
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
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
