import { useEffect, useState } from "react";

import {
  connectDhan,
  getBrokers,
  syncDhan,
  type BrokerConnection,
} from "../services/brokers";


export default function BrokerPage() {

  const [brokers, setBrokers] =
    useState<BrokerConnection[]>([]);

  const [clientId, setClientId] =
    useState("");

  const [accessToken, setAccessToken] =
    useState("");

  const [message, setMessage] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  async function loadBrokers() {

    try {

      const response =
        await getBrokers();

      setBrokers(response);

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to load brokers.",
      );

    }

  }


  useEffect(() => {
    void loadBrokers();
  }, []);


  async function connect() {

    if (!clientId || !accessToken) {
      setMessage(
        "Enter Dhan Client ID and Access Token.",
      );
      return;
    }

    try {

      setLoading(true);
      setMessage("");

      await connectDhan(
        clientId,
        accessToken,
      );

      setAccessToken("");

      setMessage(
        "Dhan connected successfully.",
      );

      await loadBrokers();

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Dhan connection failed.",
      );

    } finally {

      setLoading(false);

    }

  }


  async function synchronize() {

    try {

      setLoading(true);
      setMessage("");

      const result =
        await syncDhan();

      setMessage(
        `${result.message} ` +
        `Holdings: ${result.holdings_updated}. ` +
        `Transactions imported: ` +
        `${result.transactions_imported}.`,
      );

      await loadBrokers();

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Synchronization failed.",
      );

    } finally {

      setLoading(false);

    }

  }


  const dhan =
    brokers.find(
      (broker) =>
        broker.broker_name === "DHAN",
    );


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-4xl">

        <h1 className="text-3xl font-bold">
          Broker Connections
        </h1>

        <p className="mt-2 text-slate-600">
          Connect your trading account to synchronize
          portfolio data with TradePilot AI.
        </p>


        {message && (

          <div className="mt-5 rounded-lg bg-slate-100 p-4">
            {message}
          </div>

        )}


        <section className="mt-8 rounded-xl border bg-white p-6 shadow-sm">

          <h2 className="text-xl font-semibold">
            Dhan
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Read-only portfolio synchronization.
          </p>


          <div className="mt-5 grid gap-4">

            <input
              value={clientId}
              onChange={(event) =>
                setClientId(
                  event.target.value
                )
              }
              placeholder="Dhan Client ID"
              className="rounded-lg border px-3 py-2"
            />


            <input
              type="password"
              value={accessToken}
              onChange={(event) =>
                setAccessToken(
                  event.target.value
                )
              }
              placeholder="Dhan Access Token"
              className="rounded-lg border px-3 py-2"
            />


            <button
              type="button"
              disabled={loading}
              onClick={() => void connect()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
            >
              {loading
                ? "Connecting..."
                : "Connect Dhan"}
            </button>

          </div>

        </section>


        {dhan && (

          <section className="mt-6 rounded-xl border bg-white p-6 shadow-sm">

            <div className="flex items-center justify-between">

              <div>

                <h2 className="text-xl font-semibold">
                  Dhan Connection
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Client: {dhan.client_id}
                </p>

                <p className="mt-1 text-sm">
                  Status: {dhan.status}
                </p>

              </div>


              <button
                type="button"
                disabled={loading}
                onClick={() => void synchronize()}
                className="rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
              >
                {loading
                  ? "Syncing..."
                  : "Sync Portfolio"}
              </button>

            </div>


            {dhan.last_sync_at && (

              <p className="mt-5 text-sm text-slate-500">
                Last sync: {dhan.last_sync_at}
              </p>

            )}


            {dhan.last_sync_status && (

              <p className="mt-1 text-sm">
                Last sync status:
                {" "}
                {dhan.last_sync_status}
              </p>

            )}

          </section>

        )}


        <section className="mt-6 rounded-xl border bg-amber-50 p-5 text-sm text-amber-900">

          <strong>Security:</strong>
          {" "}
          Your Dhan access token is encrypted before
          being stored. Never commit your token or
          encryption key to GitHub.

        </section>

      </div>

    </main>
  );
}
