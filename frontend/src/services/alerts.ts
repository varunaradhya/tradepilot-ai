import { api } from "./api";

export interface AlertItem {
  id: number;
  type: string;
  severity: "INFO" | "WARNING" | "HIGH";
  symbol: string | null;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export function getAlerts(): Promise<AlertItem[]> { return api.get<AlertItem[]>("/alerts"); }
export function markAlertRead(id: number): Promise<AlertItem> { return api.post<AlertItem>(`/alerts/${id}/read`); }
export function markAllAlertsRead(): Promise<{ marked_read: number }> { return api.post<{ marked_read: number }>("/alerts/read-all"); }
