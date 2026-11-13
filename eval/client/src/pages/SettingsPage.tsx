import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Settings, ShieldCheck, Database, CheckCircle2 } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Settings className="w-6 h-6 text-sky-400" />
          <h1 className="text-2xl font-bold text-slate-100">System Configuration</h1>
        </div>
        <p className="text-sm text-slate-400">
          Audited configuration parameters, health probes, and runtime verification status.
        </p>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div>
          <h3 className="text-sm font-bold text-slate-200 mb-3 flex items-center">
            <Database className="w-4 h-4 mr-2 text-sky-400" /> Health Probes & Readiness
          </h3>
          {loading ? (
            <div className="text-xs text-slate-500">Checking health probes...</div>
          ) : health ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 font-mono text-xs">
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                <span className="text-slate-500 block text-[10px]">API Status</span>
                <span className="text-emerald-400 font-bold flex items-center mt-1">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> {health.status}
                </span>
              </div>

              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                <span className="text-slate-500 block text-[10px]">Database Connectivity</span>
                <span className="text-emerald-400 font-bold flex items-center mt-1">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> {health.database}
                </span>
              </div>

              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                <span className="text-slate-500 block text-[10px]">Active Provider</span>
                <span className="text-sky-400 font-bold mt-1 block">
                  {health.provider_mode}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-rose-400">Unable to reach backend health endpoint.</div>
          )}
        </div>

        <div className="pt-4 border-t border-slate-800 space-y-3">
          <h3 className="text-sm font-bold text-slate-200 flex items-center">
            <ShieldCheck className="w-4 h-4 mr-2 text-emerald-400" /> Security & Trust Parameters
          </h3>
          <div className="p-4 bg-slate-950/50 rounded-xl border border-slate-800 space-y-2 text-xs font-mono text-slate-400">
            <p>• Principal Isolation: Bearer tokens with SHA-256 HMAC digest salted via server-side pepper.</p>
            <p>• Prompt Injection Control: Post content treated strictly as untrusted text strings.</p>
            <p>• Commercial Integrity: LLM cannot emit ungrounded discounts; validated against approved campaigns.</p>
            <p>• Outbox Persistence: PostgreSQL jobs table with SKIP LOCKED & 120s expiring leases.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
