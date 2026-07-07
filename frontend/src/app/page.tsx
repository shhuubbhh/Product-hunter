"use client";

import { useEffect, useState, useRef } from "react";
import {
  Activity,
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Info,
  RefreshCw,
  Save,
  Send,
  Settings as SettingsIcon,
  Shield,
  ShoppingBag,
  TrendingUp,
  XCircle
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from "recharts";

// API Config
const getBackendUrls = () => {
  // If env variable is set, use it. Expected format: "ps5-hunter-backend.onrender.com" or "https://..."
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  
  if (envUrl) {
    // Strip protocol if it was included to easily construct both HTTP and WS
    const cleanUrl = envUrl.replace(/^(https?:\/\/|wss?:\/\/)/, "");
    const isHttps = envUrl.startsWith("https://") || envUrl.startsWith("wss://") || !envUrl.startsWith("http://");
    
    const httpProto = isHttps ? "https" : "http";
    const wsProto = isHttps ? "wss" : "ws";
    
    return {
      API_BASE: `${httpProto}://${cleanUrl}/api`,
      WS_BASE: `${wsProto}://${cleanUrl}/ws`
    };
  }

  // Fallback to local development behavior
  const hostname = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return {
    API_BASE: `http://${hostname}:8000/api`,
    WS_BASE: `ws://${hostname}:8000/ws`
  };
};

const { API_BASE, WS_BASE } = getBackendUrls();

interface Store {
  id: number;
  name: string;
  display_name: string;
  enabled: boolean;
  product_url: string;
  status: string;
  last_checked: string | null;
  response_time_ms: number;
  price: number | null;
  last_stock_seen: string | null;
  last_error: string | null;
}

interface Settings {
  polling_interval: number;
  notification_cooldown_minutes: number;
  telegram_enabled: boolean;
  telegram_bot_token: string | null;
  telegram_chat_id: string | null;
  discord_enabled: boolean;
  discord_webhook_url: string | null;
  email_enabled: boolean;
  smtp_host: string;
  smtp_port: number;
  smtp_username: string | null;
  smtp_password: string | null;
  smtp_sender: string;
}

interface StockHistory {
  id: number;
  store_name: string;
  product_name: string;
  price: number | null;
  timestamp: string;
  went_out_of_stock_at: string | null;
  duration_seconds: number | null;
}

interface StoreStats {
  store_name: string;
  checks_performed: number;
  successful_checks: number;
  failed_checks: number;
  uptime_percentage: number;
  avg_response_time_ms: number;
  last_stock_seen: string | null;
}

interface GlobalStats {
  checks_performed: number;
  successful_checks: number;
  failed_checks: number;
  avg_response_time_ms: number;
  last_notification: string | null;
  total_stock_detections: number;
  store_stats: StoreStats[];
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "history" | "settings">("dashboard");
  const [stores, setStores] = useState<Store[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [history, setHistory] = useState<StockHistory[]>([]);
  const [metrics, setMetrics] = useState<GlobalStats | null>(null);
  const [checkingStores, setCheckingStores] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const triggerToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchInitialData = async () => {
    try {
      const [storesRes, settingsRes, historyRes, metricsRes] = await Promise.all([
        fetch(`${API_BASE}/stores`),
        fetch(`${API_BASE}/settings`),
        fetch(`${API_BASE}/history`),
        fetch(`${API_BASE}/metrics`)
      ]);

      if (storesRes.ok) setStores(await storesRes.json());
      if (settingsRes.ok) setSettings(await settingsRes.json());
      if (historyRes.ok) setHistory(await historyRes.json());
      if (metricsRes.ok) setMetrics(await metricsRes.json());
    } catch (e) {
      console.error("Error fetching initial dashboard data", e);
      triggerToast("Error connecting to server. Please ensure backend is running.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();

    // Establish WebSocket Connection
    const connectWS = () => {
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === "store_status_checking") {
            setCheckingStores(prev => ({ ...prev, [data.store_name]: true }));
          } else if (data.type === "store_update") {
            // Update checking state
            setCheckingStores(prev => ({ ...prev, [data.store.name]: false }));
            // Update stores list
            setStores(prev => prev.map(s => s.name === data.store.name ? { ...s, ...data.store } : s));
            
            // Refresh metrics and history concurrently to keep everything in sync
            fetch(`${API_BASE}/metrics`).then(r => r.json()).then(setMetrics).catch(() => {});
            fetch(`${API_BASE}/history`).then(r => r.json()).then(setHistory).catch(() => {});
          }
        } catch (e) {
          console.error("Error parsing websocket message", e);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected. Retrying connection in 5 seconds...");
        setTimeout(connectWS, 5000);
      };
      
      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        setSettings(await res.json());
        triggerToast("Configuration saved successfully!");
      } else {
        triggerToast("Failed to save configuration", "error");
      }
    } catch (e) {
      triggerToast("Network error saving configuration", "error");
    }
  };

  const handleStoreConfigChange = async (storeId: number, fields: Partial<Store>) => {
    try {
      const res = await fetch(`${API_BASE}/stores/${storeId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields)
      });
      if (res.ok) {
        const updated = await res.json();
        setStores(prev => prev.map(s => s.id === storeId ? updated : s));
        triggerToast("Store configuration updated!");
      } else {
        triggerToast("Failed to update store configuration", "error");
      }
    } catch (e) {
      triggerToast("Error updating store configuration", "error");
    }
  };

  const sendTestNotification = async () => {
    try {
      const res = await fetch(`${API_BASE}/test-notification`, { method: "POST" });
      if (res.ok) {
        triggerToast("Test Stock Notification dispatched!");
      } else {
        triggerToast("Failed to send test notification", "error");
      }
    } catch (e) {
      triggerToast("Error dispatching test notification", "error");
    }
  };

  const getStatusColor = (status: string, isChecking: boolean) => {
    if (isChecking) return "border-yellow-500/30 bg-yellow-500/5 text-yellow-500";
    switch (status.toLowerCase()) {
      case "in stock": return "border-emerald-500/30 bg-emerald-500/5 text-emerald-400";
      case "out of stock": return "border-rose-500/30 bg-rose-500/5 text-rose-400";
      case "error": return "border-red-500/20 bg-red-500/5 text-red-400";
      default: return "border-slate-700 bg-slate-800/5 text-slate-400";
    }
  };

  const formatDuration = (sec: number | null) => {
    if (sec === null) return "N/A";
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m`;
    const hr = Math.floor(min / 60);
    return `${hr}h ${min % 60}m`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0b0f19]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
        <p className="mt-4 text-slate-400 text-sm tracking-wide">Initializing PS5 Hunter...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-7xl mx-auto px-4 py-8">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 transition-all duration-300 ${
          toast.type === "success" ? "bg-emerald-950 border-emerald-500/40 text-emerald-200" : "bg-rose-950 border-rose-500/40 text-rose-200"
        }`}>
          {toast.type === "success" ? <CheckCircle2 className="h-5 w-5 text-emerald-400" /> : <XCircle className="h-5 w-5 text-rose-400" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              PS5 HUNTER
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">24/7 Indian Retailer Stock Scanner Engine</p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-900/60 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "dashboard" ? "bg-emerald-500 text-slate-950 shadow-md" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "history" ? "bg-emerald-500 text-slate-950 shadow-md" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Stock Timeline
          </button>
          <button
            onClick={() => setActiveTab("settings")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "settings" ? "bg-emerald-500 text-slate-950 shadow-md" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Settings & Stores
          </button>
        </div>
      </header>

      {/* Tab: Dashboard */}
      {activeTab === "dashboard" && (
        <div className="space-y-8">
          {/* Stats Bar */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-medium">SCAN CYCLES</p>
                <h3 className="text-2xl font-bold mt-1 text-slate-100">{metrics?.checks_performed.toLocaleString() || "0"}</h3>
              </div>
              <Activity className="h-6 w-6 text-slate-500" />
            </div>
            <div className="glass p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-medium">AVG RESPONSE TIME</p>
                <h3 className="text-2xl font-bold mt-1 text-slate-100">{metrics?.avg_response_time_ms ? `${metrics.avg_response_time_ms}ms` : "N/A"}</h3>
              </div>
              <Clock className="h-6 w-6 text-slate-500" />
            </div>
            <div className="glass p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-medium">SUCCESS RATE</p>
                <h3 className="text-2xl font-bold mt-1 text-slate-100">
                  {metrics?.checks_performed ? `${Math.round((metrics.successful_checks / metrics.checks_performed) * 100)}%` : "100%"}
                </h3>
              </div>
              <CheckCircle2 className="h-6 w-6 text-slate-500" />
            </div>
            <div className="glass p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-medium">STOCK DETECTIONS</p>
                <h3 className="text-2xl font-bold mt-1 text-slate-100">{metrics?.total_stock_detections || "0"}</h3>
              </div>
              <TrendingUp className="h-6 w-6 text-slate-500" />
            </div>
          </div>

          {/* Stores Stock Cards Grid */}
          <div>
            <h2 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
              <ShoppingBag className="h-5 w-5 text-emerald-400" /> Retailer Availability Grid
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {stores.map((store) => {
                const isChecking = checkingStores[store.name] || false;
                const statusColor = getStatusColor(store.status, isChecking);
                return (
                  <div key={store.id} className="glass glass-hover p-6 rounded-2xl flex flex-col justify-between min-h-[220px]">
                    <div>
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-base font-bold text-slate-100">{store.display_name}</h3>
                          <span className={`inline-block mt-2 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase border ${statusColor}`}>
                            {isChecking ? "Checking..." : store.status}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500">
                          {store.response_time_ms ? `${store.response_time_ms}ms` : "-"}
                        </span>
                      </div>
                      
                      <div className="mt-5 space-y-2">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">Current Price:</span>
                          <span className="font-semibold text-slate-200">{store.price ? `₹${store.price.toLocaleString()}` : "N/A"}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">Last Checked:</span>
                          <span className="text-slate-300">
                            {store.last_checked ? new Date(store.last_checked).toLocaleTimeString() : "Never"}
                          </span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">Last Stock Seen:</span>
                          <span className="text-slate-300">
                            {store.last_stock_seen ? new Date(store.last_stock_seen).toLocaleDateString() : "Never"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-white/5 flex gap-2">
                      <a
                        href={store.product_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-semibold text-center hover:bg-slate-700 transition flex items-center justify-center gap-1.5"
                      >
                        Product Link <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      {store.status === "In Stock" && (
                        <a
                          href={store.product_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex-1 py-2 rounded-xl bg-emerald-500 text-slate-950 text-xs font-bold text-center hover:bg-emerald-400 transition shadow-lg glow-green"
                        >
                          BUY NOW
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Response Time & Uptime Analytics Charts */}
          {metrics && metrics.store_stats && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass p-6 rounded-2xl">
                <h3 className="text-sm font-semibold text-slate-300 mb-4">Response Time Comparison (ms)</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics.store_stats}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="store_name" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} />
                      <Tooltip
                        contentStyle={{ background: "#0b0f19", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }}
                        labelStyle={{ color: "#94a3b8" }}
                      />
                      <Bar dataKey="avg_response_time_ms" fill="#10b981" radius={[4, 4, 0, 0]}>
                        {metrics.store_stats.map((entry, idx) => (
                          <Cell key={`cell-${idx}`} fill={entry.avg_response_time_ms > 2000 ? "#ef4444" : "#10b981"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="glass p-6 rounded-2xl">
                <h3 className="text-sm font-semibold text-slate-300 mb-4">Uptime Scan Performance (%)</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics.store_stats}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="store_name" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" domain={[80, 100]} fontSize={10} />
                      <Tooltip
                        contentStyle={{ background: "#0b0f19", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }}
                        labelStyle={{ color: "#94a3b8" }}
                      />
                      <Bar dataKey="uptime_percentage" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: History Stock Timeline */}
      {activeTab === "history" && (
        <div className="glass p-6 rounded-2xl">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Database className="h-5 w-5 text-emerald-400" /> Stock Detections Feed
            </h2>
            <button
              onClick={fetchInitialData}
              className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          {history.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-white/5 rounded-2xl">
              <Info className="h-8 w-8 text-slate-500 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">No stock events recorded yet.</p>
              <p className="text-slate-500 text-xs mt-1">PS5 Hunter will populate timeline when items become available.</p>
            </div>
          ) : (
            <div className="relative border-l border-white/5 pl-6 ml-4 space-y-8">
              {history.map((item) => (
                <div key={item.id} className="relative">
                  <span className="absolute -left-[31px] top-1.5 h-3.5 w-3.5 rounded-full border border-[#0b0f19] bg-emerald-500 glow-green"></span>
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-bold text-slate-100">{item.product_name}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Store: <span className="text-slate-200 font-semibold">{item.store_name}</span> &bull; Price:{" "}
                        <span className="text-emerald-400 font-semibold">{item.price ? `₹${item.price.toLocaleString()}` : "N/A"}</span>
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-300 font-medium">
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5 flex items-center justify-end gap-1.5">
                        <Clock className="h-3 w-3" /> Duration in stock:{" "}
                        <span className="font-semibold text-slate-400">{formatDuration(item.duration_seconds)}</span>
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Settings & Configs */}
      {activeTab === "settings" && settings && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* System settings form */}
          <div className="lg:col-span-2 space-y-6">
            <form onSubmit={saveSettings} className="glass p-6 rounded-2xl space-y-6">
              <h2 className="text-base font-bold text-slate-200 flex items-center gap-2 border-b border-white/5 pb-4">
                <SettingsIcon className="h-5 w-5 text-emerald-400" /> Scanner & Channel Preferences
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase">Poll Frequency (Seconds)</label>
                  <input
                    type="number"
                    min="5"
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                    value={settings.polling_interval}
                    onChange={(e) => setSettings({ ...settings, polling_interval: parseInt(e.target.value) || 20 })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase">Alert Cooldown (Minutes)</label>
                  <input
                    type="number"
                    min="0"
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                    value={settings.notification_cooldown_minutes}
                    onChange={(e) => setSettings({ ...settings, notification_cooldown_minutes: parseInt(e.target.value) || 10 })}
                  />
                </div>
              </div>

              {/* Telegram Channel */}
              <div className="space-y-4 pt-4 border-t border-white/5">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-blue-500"></span>
                    <h3 className="text-sm font-semibold text-slate-300">Telegram Bot Notifications</h3>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.telegram_enabled}
                    onChange={(e) => setSettings({ ...settings, telegram_enabled: e.target.checked })}
                    className="h-4 w-4 accent-emerald-500"
                  />
                </div>
                {settings.telegram_enabled && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fadeIn">
                    <div>
                      <label className="block text-xs text-slate-400">Bot Token</label>
                      <input
                        type="text"
                        placeholder="123456:ABC-DEF"
                        className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                        value={settings.telegram_bot_token || ""}
                        onChange={(e) => setSettings({ ...settings, telegram_bot_token: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400">Chat ID</label>
                      <input
                        type="text"
                        placeholder="@channel_name or id"
                        className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                        value={settings.telegram_chat_id || ""}
                        onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Discord Webhook */}
              <div className="space-y-4 pt-4 border-t border-white/5">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-indigo-500"></span>
                    <h3 className="text-sm font-semibold text-slate-300">Discord Webhook Alerts</h3>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.discord_enabled}
                    onChange={(e) => setSettings({ ...settings, discord_enabled: e.target.checked })}
                    className="h-4 w-4 accent-emerald-500"
                  />
                </div>
                {settings.discord_enabled && (
                  <div>
                    <label className="block text-xs text-slate-400">Webhook URL</label>
                    <input
                      type="text"
                      placeholder="https://discord.com/api/webhooks/..."
                      className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                      value={settings.discord_webhook_url || ""}
                      onChange={(e) => setSettings({ ...settings, discord_webhook_url: e.target.value })}
                    />
                  </div>
                )}
              </div>

              {/* SMTP Email Configuration */}
              <div className="space-y-4 pt-4 border-t border-white/5">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <h3 className="text-sm font-semibold text-slate-300">SMTP Email Delivery</h3>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.email_enabled}
                    onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
                    className="h-4 w-4 accent-emerald-500"
                  />
                </div>
                {settings.email_enabled && (
                  <div className="space-y-4 animate-fadeIn">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="md:col-span-2">
                        <label className="block text-xs text-slate-400">SMTP Host</label>
                        <input
                          type="text"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                          value={settings.smtp_host}
                          onChange={(e) => setSettings({ ...settings, smtp_host: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400">Port</label>
                        <input
                          type="number"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                          value={settings.smtp_port}
                          onChange={(e) => setSettings({ ...settings, smtp_port: parseInt(e.target.value) || 587 })}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-slate-400">SMTP User / Username</label>
                        <input
                          type="text"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                          value={settings.smtp_username || ""}
                          onChange={(e) => setSettings({ ...settings, smtp_username: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400">SMTP Password</label>
                        <input
                          type="password"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 mt-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
                          value={settings.smtp_password || ""}
                          onChange={(e) => setSettings({ ...settings, smtp_password: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-4 pt-4 border-t border-white/5">
                <button
                  type="submit"
                  className="flex-1 py-3 rounded-xl bg-emerald-500 text-slate-950 text-xs font-bold hover:bg-emerald-400 transition flex items-center justify-center gap-2"
                >
                  <Save className="h-4 w-4" /> Save System Preferences
                </button>
                <button
                  type="button"
                  onClick={sendTestNotification}
                  className="px-6 py-3 rounded-xl bg-slate-800 text-slate-200 text-xs font-semibold hover:bg-slate-700 transition flex items-center justify-center gap-2 border border-white/5"
                >
                  <Send className="h-4 w-4" /> Test Alert
                </button>
              </div>
            </form>
          </div>

          {/* Store configuration list */}
          <div className="space-y-6">
            <div className="glass p-6 rounded-2xl">
              <h2 className="text-base font-bold text-slate-200 flex items-center gap-2 border-b border-white/5 pb-4 mb-4">
                <Shield className="h-5 w-5 text-emerald-400" /> Active Store Rules
              </h2>
              <div className="space-y-4">
                {stores.map((store) => (
                  <div key={store.id} className="p-4 bg-slate-900/50 rounded-xl border border-white/5 space-y-3">
                    <div className="flex justify-between items-center">
                      <h4 className="text-sm font-bold text-slate-200">{store.display_name}</h4>
                      <input
                        type="checkbox"
                        checked={store.enabled}
                        onChange={(e) => handleStoreConfigChange(store.id, { enabled: e.target.checked })}
                        className="h-4 w-4 accent-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase font-semibold text-slate-500">Target Product URL</label>
                      <input
                        type="text"
                        className="w-full bg-slate-950 border border-white/5 rounded-lg px-3 py-1.5 mt-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                        value={store.product_url}
                        onChange={(e) => setStores(prev => prev.map(s => s.id === store.id ? { ...s, product_url: e.target.value } : s))}
                        onBlur={() => handleStoreConfigChange(store.id, { product_url: store.product_url })}
                      />
                    </div>
                    {(store.name === "blinkit" || store.name === "zepto") && (
                      <div>
                        <label className="block text-[10px] uppercase font-semibold text-slate-500">Delivery Pincode</label>
                        <input
                          type="text"
                          placeholder="e.g. 110001"
                          maxLength={6}
                          className="w-full bg-slate-950 border border-white/5 rounded-lg px-3 py-1.5 mt-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                          value={(() => {
                            try {
                              const parsed = JSON.parse(store.custom_headers || "{}");
                              return parsed.pincode || "";
                            } catch {
                              return store.custom_headers || "";
                            }
                          })()}
                          onChange={(e) => {
                            const val = e.target.value;
                            setStores(prev => prev.map(s => {
                              if (s.id === store.id) {
                                let newHeaders = "";
                                try {
                                  const parsed = JSON.parse(s.custom_headers || "{}");
                                  parsed.pincode = val;
                                  newHeaders = JSON.stringify(parsed);
                                } catch {
                                  newHeaders = JSON.stringify({ pincode: val });
                                }
                                return { ...s, custom_headers: newHeaders };
                              }
                              return s;
                            }));
                          }}
                          onBlur={() => {
                            handleStoreConfigChange(store.id, { custom_headers: store.custom_headers });
                          }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
