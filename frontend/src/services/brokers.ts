import { api } from "./api";


export interface BrokerConnection {
  id: number;
  broker_name: string;
  client_id: string;
  status: string;
  token_expires_at: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_message: string | null;
}


export interface BrokerSyncResult {
  broker_name: string;
  status: string;
  holdings_imported: number;
  transactions_imported: number;
  holdings_updated: number;
  message: string;
  synced_at: string;
}


export async function getBrokers() {

  return api.get<BrokerConnection[]>(
    "/brokers",
  );

}


export async function connectDhan(
  clientId: string,
  accessToken: string,
) {

  return api.post<BrokerConnection>(
    "/brokers/connect",
    {
      broker_name: "DHAN",
      client_id: clientId,
      access_token: accessToken,
    },
  );

}


export async function syncDhan() {

  return api.post<BrokerSyncResult>(
    "/brokers/dhan/sync",
  );

}
