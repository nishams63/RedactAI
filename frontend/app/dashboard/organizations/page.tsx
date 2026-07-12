"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api";
import { formatDate } from "@/lib/utils";
import { Building2, Mail, Phone, MapPin, Globe } from "lucide-react";

export default function OrganizationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiClient.getOrganizations(),
  });

  const organizations = data?.organizations || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold">Organizations</h1>
        <p className="text-[rgb(var(--text-secondary))] mt-1">
          Manage organizations within your platform
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="glass-card p-6 space-y-4">
              <div className="w-full h-6 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
              <div className="w-3/4 h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
              <div className="w-1/2 h-4 bg-[rgb(var(--bg-secondary))] rounded animate-pulse" />
            </div>
          ))}
        </div>
      ) : organizations.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Building2 className="w-16 h-16 mx-auto text-[rgb(var(--text-secondary))]/30 mb-4" />
          <p className="text-lg font-semibold mb-2">No organizations yet</p>
          <p className="text-[rgb(var(--text-secondary))] text-sm">Organizations will appear here once created</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {organizations.map((org: any) => (
            <div key={org.id} className="glass-card-hover p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-brand-400 to-indigo-500 rounded-xl flex items-center justify-center text-white font-bold text-lg">
                  {org.name?.charAt(0)?.toUpperCase()}
                </div>
                <div>
                  <h3 className="font-bold text-lg">{org.name}</h3>
                  <p className="text-xs text-[rgb(var(--text-secondary))]">Created {formatDate(org.created_at)}</p>
                </div>
              </div>
              <div className="space-y-2 text-sm text-[rgb(var(--text-secondary))]">
                {org.email && (
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 shrink-0" />
                    <span className="truncate">{org.email}</span>
                  </div>
                )}
                {org.phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 shrink-0" />
                    <span>{org.phone}</span>
                  </div>
                )}
                {org.address && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 shrink-0" />
                    <span className="truncate">{org.address}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
