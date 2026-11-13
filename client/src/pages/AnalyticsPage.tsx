import React, { useState, useEffect } from 'react';
import { AnalyticsSummary } from '../types';
import { api } from '../api/client';
import { Activity, CheckCircle, MessageSquare, Zap, Cpu, Server, Clock } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="text-center py-16 text-xs text-slate-500">Loading system metrics...</div>;
  }

  const { overview, system } = data;

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Activity className="w-6 h-6 text-sky-400" />
          <h1 className="text-2xl font-bold text-slate-100">System Analytics & Observability</h1>
        </div>
        <p className="text-sm text-slate-400">
          Delivery rates, autonomous engagement statistics, queue performance, and model telemetry.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase">Total Posts</span>
            <Server className="w-4 h-4 text-sky-400" />
          </div>
          <span className="text-2xl font-bold text-slate-100">{overview.total_posts}</span>
          <span className="text-[11px] text-slate-500 block mt-1">Across 5 demo agents</span>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase">Delivered Notifications</span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-2xl font-bold text-slate-100">{overview.delivered_notifications}</span>
          <span className="text-[11px] text-emerald-400 block mt-1">
            {overview.delivery_rate_pct}% delivery rate
          </span>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase">Grounded Comments</span>
            <MessageSquare className="w-4 h-4 text-indigo-400" />
          </div>
          <span className="text-2xl font-bold text-slate-100">{overview.total_comments}</span>
          <span className="text-[11px] text-indigo-400 block mt-1">
            {overview.engagement_rate_pct}% engagement rate
          </span>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase">Avg LLM Latency</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <span className="text-2xl font-bold text-slate-100">{overview.avg_llm_duration_ms} ms</span>
          <span className="text-[11px] text-amber-400 block mt-1">Per recipient decision</span>
        </div>
      </div>

      {/* Configuration & Model Specs */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-200 flex items-center">
          <Cpu className="w-4 h-4 mr-2 text-sky-400" /> Active Architecture Configuration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-500">Routing Policy:</span>
              <span className="text-sky-400 font-bold">{system.routing_policy}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Embedding Engine:</span>
              <span className="text-slate-300">{system.embedding_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Vector Dimension:</span>
              <span className="text-slate-300">384 dimensions</span>
            </div>
          </div>

          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-500">Generation Provider:</span>
              <span className="text-sky-400 font-bold">{system.llm_provider.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Generation Model:</span>
              <span className="text-slate-300">{system.llm_model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Pending Job Queue:</span>
              <span className="text-emerald-400 font-bold">{overview.pending_jobs} jobs</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

