"use client";

import { accountsApi } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Plus,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  Users,
  Mail,
} from "lucide-react";

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [newAccount, setNewAccount] = useState({
    email: "",
    access_token: "",
    refresh_token: "",
    client_id: "",
    client_secret: "",
  });

  const { data: accounts, isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => accountsApi.getAll().then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: (data: typeof newAccount) => accountsApi.add(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setShowAddModal(false);
      setNewAccount({ email: "", access_token: "", refresh_token: "", client_id: "", client_secret: "" });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => accountsApi.pause(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => accountsApi.resume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => accountsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const resetDailyMutation = useMutation({
    mutationFn: (id: string) => accountsApi.resetDaily(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const activeAccounts = accounts?.filter((a) => a.status === "active") || [];
  const pausedAccounts = accounts?.filter((a) => a.status === "paused") || [];

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Accounts</h1>
            <p className="text-muted-foreground">Manage your Gmail accounts</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add Account
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-full">
                <Users className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold">{activeAccounts.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-100 rounded-full">
                <Users className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Paused</p>
                <p className="text-2xl font-bold">{pausedAccounts.length}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-card rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Email</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Daily</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Hourly</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Last Sent</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center">Loading...</td>
                </tr>
              ) : accounts?.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No accounts added yet</td>
                </tr>
              ) : (
                accounts?.map((account) => (
                  <tr key={account.id} className="border-t">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{account.email}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${account.status === "active" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>
                        {account.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">{account.daily_sent_count}</td>
                    <td className="px-4 py-3">{account.hourly_sent_count}</td>
                    <td className="px-4 py-3">{account.last_sent_at ? new Date(account.last_sent_at).toLocaleString() : "Never"}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {account.status === "active" ? (
                          <button onClick={() => pauseMutation.mutate(account.id)} disabled={pauseMutation.isPending} className="p-1 text-yellow-600 hover:bg-yellow-50 rounded" title="Pause">
                            <Pause className="h-4 w-4" />
                          </button>
                        ) : (
                          <button onClick={() => resumeMutation.mutate(account.id)} disabled={resumeMutation.isPending} className="p-1 text-green-600 hover:bg-green-50 rounded" title="Resume">
                            <Play className="h-4 w-4" />
                          </button>
                        )}
                        <button onClick={() => resetDailyMutation.mutate(account.id)} disabled={resetDailyMutation.isPending} className="p-1 text-blue-600 hover:bg-blue-50 rounded" title="Reset Daily">
                          <RefreshCw className="h-4 w-4" />
                        </button>
                        <button onClick={() => { if (confirm("Delete this account?")) deleteMutation.mutate(account.id); }} disabled={deleteMutation.isPending} className="p-1 text-red-600 hover:bg-red-50 rounded" title="Delete">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card rounded-lg border p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold mb-4">Add Gmail Account</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Email Address</label>
                  <input type="email" value={newAccount.email} onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-background" placeholder="your@gmail.com" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Access Token</label>
                  <input type="password" value={newAccount.access_token} onChange={(e) => setNewAccount({ ...newAccount, access_token: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-background" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Refresh Token</label>
                  <input type="password" value={newAccount.refresh_token} onChange={(e) => setNewAccount({ ...newAccount, refresh_token: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-background" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Client ID (for this account)</label>
                  <input type="password" value={newAccount.client_id} onChange={(e) => setNewAccount({ ...newAccount, client_id: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-background" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Client Secret (for this account)</label>
                  <input type="password" value={newAccount.client_secret} onChange={(e) => setNewAccount({ ...newAccount, client_secret: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-background" />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button onClick={() => setShowAddModal(false)} className="px-4 py-2 border rounded-md hover:bg-muted">Cancel</button>
                <button onClick={() => addMutation.mutate(newAccount)} disabled={addMutation.isPending} className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50">Add Account</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}