import React, { useState, useEffect } from 'react';
import { Post, RouteInspectorData } from '../types';
import { api } from '../api/client';
import { RouteTable } from '../components/RouteTable';
import { Layers, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

interface InspectorPageProps {
  posts: Post[];
  selectedPostId: string | null;
  onSelectPost: (postId: string) => void;
}

export const InspectorPage: React.FC<InspectorPageProps> = ({
  posts,
  selectedPostId,
  onSelectPost
}) => {
  const activePostId = selectedPostId || posts[0]?.id || '';
  const [data, setData] = useState<RouteInspectorData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRouting = async (postId: string) => {
    if (!postId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.getPostRouting(postId);
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Routing decisions not available yet.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activePostId) {
      loadRouting(activePostId);
    }
  }, [activePostId]);

  const activePost = posts.find((p) => p.id === activePostId);

  return (
    <div className="space-y-6">
      {/* Header & Post Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-6 h-6 text-sky-400" />
            <h1 className="text-2xl font-bold text-slate-100">Semantic Route Inspector</h1>
          </div>
          <p className="text-sm text-slate-400">
            Explainable decision records, similarity vectors, and candidate scoring arithmetic.
          </p>
        </div>

        {/* Post Dropdown */}
        <div className="flex items-center space-x-2">
          <label className="text-xs font-semibold text-slate-400">Inspecting Post:</label>
          <select
            value={activePostId}
            onChange={(e) => onSelectPost(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500 max-w-xs"
          >
            {posts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.author_name}: {p.title.substring(0, 40)}...
              </option>
            ))}
          </select>
          <button
            onClick={() => loadRouting(activePostId)}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Reload inspection"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Active Post Summary Card */}
      {activePost && (
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-sky-400">Target Post</span>
            <h3 className="text-base font-bold text-slate-100">{activePost.title}</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">{activePost.content}</p>
          </div>
          <div className="flex flex-wrap gap-1">
            {activePost.topics.map((t) => (
              <span key={t} className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                #{t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metadata Badges */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Policy Version</span>
            <span className="text-sm font-mono font-bold text-sky-400">{data.policy_version}</span>
          </div>

          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Embedding Model</span>
            <span className="text-xs font-mono font-bold text-slate-200">MiniLM-L6-v2 (384d)</span>
          </div>

          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Candidates Evaluated</span>
            <span className="text-sm font-mono font-bold text-slate-200">{data.candidate_count} Agents</span>
          </div>

          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Selected Recipients</span>
            <span className="text-sm font-mono font-bold text-emerald-400">
              {data.selected_count} Selected
            </span>
          </div>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="text-center py-16 text-slate-400 text-xs">
          Computing vector similarities and business compatibility...
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900/60 rounded-xl border border-slate-800 text-center">
          <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">{error}</p>
          <p className="text-xs text-slate-500 mt-1">
            Ensure background workers have processed the ROUTE_POST job.
          </p>
        </div>
      ) : data ? (
        <div className="space-y-4">
          <RouteTable decisions={data.decisions} policyVersion={data.policy_version} />

          {/* Formula Rationale Box */}
          <div className="p-4 bg-slate-900/40 rounded-xl border border-slate-800/80 text-xs text-slate-400 space-y-1 font-mono">
            <p className="font-semibold text-slate-300">Policy Arithmetic: S = 0.65 · D + 0.20 · T + 0.15 · B</p>
            <p>• D: max(0, cosine_similarity) between post 384-d vector and agent profile vector.</p>
            <p>• T: Topic overlap ratio with agent include_topics.</p>
            <p>• B: Explicit business intent compatibility rule match (1.0 or 0.0).</p>
            <p>• Threshold: 0.60 | Recipient Cap: 10</p>
          </div>
        </div>
      ) : null}
    </div>
  );
};
