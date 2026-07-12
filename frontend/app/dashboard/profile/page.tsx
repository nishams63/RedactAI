"use client";

import React, { useState } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { User, Mail, Building2, Shield, Lock, Save, Eye, EyeOff } from "lucide-react";

export default function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");

  const updateProfile = useMutation({
    mutationFn: () => apiClient.updateProfile({ full_name: fullName }),
    onSuccess: () => {
      setProfileMsg("Profile updated successfully");
      refreshProfile();
      setTimeout(() => setProfileMsg(""), 3000);
    },
    onError: (err: Error) => setProfileMsg(err.message),
  });

  const changePassword = useMutation({
    mutationFn: () => apiClient.changePassword({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: () => {
      setPasswordMsg("Password changed successfully");
      setCurrentPassword("");
      setNewPassword("");
      setTimeout(() => setPasswordMsg(""), 3000);
    },
    onError: (err: Error) => setPasswordMsg(err.message),
  });

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold">Profile</h1>
        <p className="text-[rgb(var(--text-secondary))] mt-1">Manage your account settings</p>
      </div>

      {/* Profile Card */}
      <div className="glass-card p-8">
        <div className="flex items-center gap-6 mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-2xl flex items-center justify-center text-white font-bold text-3xl shadow-lg shadow-brand-500/20">
            {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div>
            <h2 className="text-2xl font-bold">{user?.full_name}</h2>
            <p className="text-[rgb(var(--text-secondary))]">{user?.email}</p>
            <div className="flex items-center gap-2 mt-2">
              {user?.roles?.map((role) => (
                <span key={role} className="badge-info">{role}</span>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-[rgb(var(--bg-secondary))]">
            <Mail className="w-5 h-5 text-[rgb(var(--text-secondary))]" />
            <div>
              <p className="text-xs text-[rgb(var(--text-secondary))]">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-[rgb(var(--bg-secondary))]">
            <Building2 className="w-5 h-5 text-[rgb(var(--text-secondary))]" />
            <div>
              <p className="text-xs text-[rgb(var(--text-secondary))]">Organization</p>
              <p className="font-medium">{user?.organization_name || "—"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-[rgb(var(--bg-secondary))]">
            <Shield className="w-5 h-5 text-[rgb(var(--text-secondary))]" />
            <div>
              <p className="text-xs text-[rgb(var(--text-secondary))]">Role</p>
              <p className="font-medium">{user?.roles?.join(", ") || "—"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-[rgb(var(--bg-secondary))]">
            <User className="w-5 h-5 text-[rgb(var(--text-secondary))]" />
            <div>
              <p className="text-xs text-[rgb(var(--text-secondary))]">Status</p>
              <p className="font-medium">{user?.is_active ? "Active" : "Inactive"}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Profile */}
      <div className="glass-card p-8">
        <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
          <User className="w-5 h-5 text-brand-500" /> Edit Profile
        </h3>
        <form onSubmit={(e) => { e.preventDefault(); updateProfile.mutate(); }} className="space-y-4">
          <div>
            <label htmlFor="editName" className="block text-sm font-semibold mb-2">Full Name</label>
            <input id="editName" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              className="input-field" required />
          </div>
          {profileMsg && (
            <p className={`text-sm font-medium ${profileMsg.includes("success") ? "text-emerald-500" : "text-red-500"}`}>
              {profileMsg}
            </p>
          )}
          <button type="submit" disabled={updateProfile.isPending} className="btn-primary">
            {updateProfile.isPending ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <><Save className="w-4 h-4" /> Save Changes</>
            )}
          </button>
        </form>
      </div>

      {/* Change Password */}
      <div className="glass-card p-8">
        <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
          <Lock className="w-5 h-5 text-brand-500" /> Change Password
        </h3>
        <form onSubmit={(e) => { e.preventDefault(); changePassword.mutate(); }} className="space-y-4">
          <div>
            <label htmlFor="currentPw" className="block text-sm font-semibold mb-2">Current Password</label>
            <div className="relative">
              <input id="currentPw" type={showCurrentPw ? "text" : "password"} value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)} className="input-field pr-12" required />
              <button type="button" onClick={() => setShowCurrentPw(!showCurrentPw)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[rgb(var(--text-secondary))]">
                {showCurrentPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          <div>
            <label htmlFor="newPw" className="block text-sm font-semibold mb-2">New Password</label>
            <div className="relative">
              <input id="newPw" type={showNewPw ? "text" : "password"} value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)} className="input-field pr-12" required minLength={8} />
              <button type="button" onClick={() => setShowNewPw(!showNewPw)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[rgb(var(--text-secondary))]">
                {showNewPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          {passwordMsg && (
            <p className={`text-sm font-medium ${passwordMsg.includes("success") ? "text-emerald-500" : "text-red-500"}`}>
              {passwordMsg}
            </p>
          )}
          <button type="submit" disabled={changePassword.isPending} className="btn-primary">
            {changePassword.isPending ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <><Lock className="w-4 h-4" /> Change Password</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
