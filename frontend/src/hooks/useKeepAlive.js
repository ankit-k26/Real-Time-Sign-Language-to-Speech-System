/**
 * useKeepAlive
 *
 * Pings the backend's /health endpoint on a fixed interval to prevent
 * Render's free-tier from spinning down the service due to inactivity.
 *
 * Default interval: 7 minutes (420 000 ms)
 * The ping is also fired immediately on mount so we know the backend
 * is reachable as soon as the app loads.
 */

import { useEffect } from "react";

const PING_INTERVAL_MS = 7 * 60 * 1000; // 7 minutes

export default function useKeepAlive(intervalMs = PING_INTERVAL_MS) {
  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL;

    if (!baseUrl) {
      console.warn("[useKeepAlive] VITE_API_BASE_URL is not set — skipping keep-alive.");
      return;
    }

    const ping = async () => {
      try {
        const res = await fetch(`${baseUrl}/health`, { method: "GET" });
        if (res.ok) {
          console.debug(`[useKeepAlive] ✅ Backend alive — ${new Date().toLocaleTimeString()}`);
        } else {
          console.warn(`[useKeepAlive] ⚠️  /health responded with status ${res.status}`);
        }
      } catch (err) {
        console.warn("[useKeepAlive] ❌ Could not reach backend:", err.message);
      }
    };

    // Fire immediately on mount, then on every interval
    ping();
    const timerId = setInterval(ping, intervalMs);

    return () => clearInterval(timerId);
  }, [intervalMs]);
}
