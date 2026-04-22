"use client";

import { logsApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Filter,
  Mail,
} from "lucide-react";

export default function LogsPage() {
  const [hours, setHours] = useState(24);
  const [filter, setFilter] = useState<"all" | "sent" | "failed">("all");

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ["logs", hours],
    queryFn: () => logsApi.getRecent({ hours, limit: 100 }).then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: stats } = useQuery({
    queryKey: ["logs", "stats"],
    queryFn: () => logsApi.getStats().then((r) => r.data),
    refetchInterval: 10000,
  });

  const filteredLogs = logs?.filter((log) => filter === "all" || log.status === filter) || [];

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Logs</h1>
            <p className="text-muted-foreground">Email activity logs</p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-card rounded-lg border p-6">
            <p className="text-sm text-muted-foreground">24h Sent</p>
            <p className="text-3xl font-bold text-green-600">{stats?.sent_24h || 0}</p>
          </div>
          <div className="bg-card rounded-lg border p-6">
            <p className="text-sm text-muted-foreground">24h Failed</p>
            <p className="text-3xl font-bold text-red-600">{stats?.failed_24h || 0}</p>
          </div>
          <div className="bg-card rounded-lg border p-6">
            <p className="text-sm text-muted-foreground">Initial</p>
            <p className="text-3xl font-bold">{stats?.by_type?.initial || 0}</p>
          </div>
          <div className="bg-card rounded-lg border p-6">
            <p className="text-sm text-muted-foreground">Follow-ups</p>
            <p className="text-3xl font-bold">{(stats?.by_type?.followup1 || 0) + (stats?.by_type?.followup2 || 0)}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mb-4">
          <select
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="px-3 py-2 border rounded-md bg-background"
          >
            <option value={1}>Last 1 hour</option>
            <option value={6}>Last 6 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={72}>Last 3 days</option>
          </select>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-3 py-2 border rounded-md bg-background"
          >
            <option value="all">All</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {/* Logs Table */}
        <div className="bg-card rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Lead</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Time</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center">Loading...</td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">No logs found</td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="border-t">
                    <td className="px-4 py-3">
                      {log.status === "sent" ? (
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-4 w-4" />
                          Sent
                        </span>
                      ) : log.status === "failed" ? (
                        <span className="flex items-center gap-1 text-red-600">
                          <XCircle className="h-4 w-4" />
                          Failed
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-yellow-600">
                          <Clock className="h-4 w-4" />
                          Pending
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{log.lead_email}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded text-xs bg-muted">{log.type}</span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-red-500 text-sm max-w-xs truncate">
                      {log.error_message || "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}