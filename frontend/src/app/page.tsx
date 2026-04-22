"use client";

import { campaignApi, accountsApi, logsApi } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Play,
  Pause,
  Square,
  RefreshCw,
  Mail,
  Users,
  Activity,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { useState } from "react";

export default function HomePage() {
  const queryClient = useQueryClient();
  const [spreadsheetId, setSpreadsheetId] = useState("");

  // Queries
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["campaign", "status"],
    queryFn: () => campaignApi.getStatus().then((r) => r.data),
    refetchInterval: 5000,
  });

  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => accountsApi.getAll().then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ["logs", "recent"],
    queryFn: () => logsApi.getRecent({ hours: 24, limit: 20 }).then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: logStats } = useQuery({
    queryKey: ["logs", "stats"],
    queryFn: () => logsApi.getStats().then((r) => r.data),
    refetchInterval: 10000,
  });

  // Mutations
  const startMutation = useMutation({
    mutationFn: () => campaignApi.start(spreadsheetId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaign"] }),
  });

  const pauseMutation = useMutation({
    mutationFn: () => campaignApi.pause(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaign"] }),
  });

  const resumeMutation = useMutation({
    mutationFn: () => campaignApi.resume(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaign"] }),
  });

  const stopMutation = useMutation({
    mutationFn: () => campaignApi.stop(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaign"] }),
  });

  const activeAccounts = accounts?.filter((a) => a.status === "active") || [];
  const pausedAccounts = accounts?.filter((a) => a.status === "paused") || [];
  const todaySent = status?.today_emails_sent || 0;

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">
              Email outreach automation system
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                status?.is_running ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-sm font-medium">
              {status?.is_running
                ? status?.is_paused
                  ? "Paused"
                  : "Running"
                : "Stopped"}
            </span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Sent Today"
            value={todaySent}
            icon={<Mail className="h-4 w-4" />}
          />
          <StatCard
            title="Active Accounts"
            value={activeAccounts.length}
            icon={<Users className="h-4 w-4" />}
          />
          <StatCard
            title="Paused Accounts"
            value={pausedAccounts.length}
            icon={<Users className="h-4 w-4" />}
          />
          <StatCard
            title="Status"
            value={status?.is_running ? (status?.is_paused ? "Paused" : "Running") : "Stopped"}
            icon={<Activity className="h-4 w-4" />}
            variant={status?.is_running ? "success" : "default"}
          />
        </div>

        {/* Campaign Control */}
        <div className="bg-card rounded-lg border p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Campaign Control</h2>
          
          {!status?.is_running ? (
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Google Sheets Spreadsheet ID"
                value={spreadsheetId}
                onChange={(e) => setSpreadsheetId(e.target.value)}
                className="flex-1 px-4 py-2 border rounded-md bg-background"
              />
              <button
                onClick={() => startMutation.mutate()}
                disabled={!spreadsheetId || startMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                Start
              </button>
            </div>
          ) : status?.is_paused ? (
            <div className="flex gap-4">
              <button
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                Resume
              </button>
              <button
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Square className="h-4 w-4" />
                Stop
              </button>
            </div>
          ) : (
            <div className="flex gap-4">
              <button
                onClick={() => pauseMutation.mutate()}
                disabled={pauseMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
              >
                <Pause className="h-4 w-4" />
                Pause
              </button>
              <button
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Square className="h-4 w-4" />
                Stop
              </button>
            </div>
          )}
        </div>

        {/* Recent Logs */}
        <div className="bg-card rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
          
          <div className="space-y-2">
            {logsLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : logs?.length === 0 ? (
              <p className="text-muted-foreground">No recent activity</p>
            ) : (
              logs?.map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div className="flex items-center gap-3">
                    {log.status === "sent" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : log.status === "failed" ? (
                      <XCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Clock className="h-4 w-4 text-yellow-500" />
                    )}
                    <div>
                      <p className="font-medium">{log.lead_email}</p>
                      <p className="text-sm text-muted-foreground">
                        {log.type} via {log.account_id}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </p>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        log.status === "sent"
                          ? "bg-green-100 text-green-800"
                          : log.status === "failed"
                          ? "bg-red-100 text-red-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {log.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="bg-card rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">24h Sent</p>
            <p className="text-2xl font-bold">{logStats?.sent_24h || 0}</p>
          </div>
          <div className="bg-card rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">24h Failed</p>
            <p className="text-2xl font-bold">{logStats?.failed_24h || 0}</p>
          </div>
          <div className="bg-card rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">24h Total</p>
            <p className="text-2xl font-bold">{logStats?.total_24h || 0}</p>
          </div>
        </div>
      </div>
    </main>
  );
}

function StatCard({
  title,
  value,
  icon,
  variant = "default",
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  variant?: "default" | "success";
}) {
  return (
    <div className="bg-card rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{title}</p>
        <span className="text-muted-foreground">{icon}</span>
      </div>
      <p
        className={`text-2xl font-bold mt-1 ${
          variant === "success" ? "text-green-600" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}