// API client for backend communication

import axios from "axios";
import type {
  GmailAccount,
  CampaignStatus,
  EmailLog,
  Lead,
  LogStats,
} from "@/types";

// Default API base URL - override with env var in production
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Campaign API
export const campaignApi = {
  start: (spreadsheetId: string) =>
    api.post("/campaign/start", { spreadsheet_id: spreadsheetId }),
  pause: () => api.post("/campaign/pause"),
  resume: () => api.post("/campaign/resume"),
  stop: () => api.post("/campaign/stop"),
  getStatus: () => api.get<CampaignStatus>("/campaign/status"),
  skipToday: () => api.post("/campaign/skip-today"),
  clearSkipToday: () => api.delete("/campaign/skip-today"),
};

// Accounts API
export const accountsApi = {
  getAll: () => api.get<GmailAccount[]>("/accounts"),
  getActive: () => api.get<GmailAccount[]>("/accounts/active"),
  get: (id: string) => api.get<GmailAccount>(`/accounts/${id}`),
  add: (data: {
    email: string;
    access_token: string;
    refresh_token: string;
    token_uri?: string;
  }) => api.post<GmailAccount>("/accounts", data),
  pause: (id: string) => api.post<GmailAccount>(`/accounts/${id}/pause`),
  resume: (id: string) => api.post<GmailAccount>(`/accounts/${id}/resume`),
  delete: (id: string) => api.delete(`/accounts/${id}`),
  resetDaily: (id: string) => api.post<GmailAccount>(`/accounts/${id}/reset-daily`),
  resetHourly: (id: string) => api.post<GmailAccount>(`/accounts/${id}/reset-hourly`),
};

// Logs API
export const logsApi = {
  getAll: (params?: { limit?: number; offset?: number }) =>
    api.get<EmailLog[]>("/logs", { params }),
  getRecent: (params?: { hours?: number; limit?: number }) =>
    api.get<EmailLog[]>("/logs/recent", { params }),
  getStats: () => api.get<LogStats>("/logs/stats"),
  getByLead: (email: string) => api.get<EmailLog[]>(`/logs/by-lead/${email}`),
};

// Leads API
export const leadsApi = {
  getAll: (params?: { status?: string; followup_stage?: string }) =>
    api.get<Lead[]>("/leads", { params }),
  getPending: () => api.get<Lead[]>("/leads/pending"),
  getForFollowup: (stage: string) => api.get<Lead[]>(`/leads/followup/${stage}`),
  sync: (spreadsheetId: string) =>
    api.post<{ total_leads: number; leads: Lead[] }>("/leads/sync", null, {
      params: { spreadsheet_id: spreadsheetId },
    }),
  configure: (spreadsheetId: string) =>
    api.post<{ status: string }>("/leads/configure", { spreadsheet_id: spreadsheetId }),
  markContacted: (email: string, followupStage?: string) =>
    api.post(`/leads/${email}/mark-contacted`, null, {
      params: { followup_stage: followupStage || "initial" },
    }),
};

export default api;