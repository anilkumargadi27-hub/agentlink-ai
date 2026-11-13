import React from 'react';
import { RouteDecision } from '../types';
import { CheckCircle2, XCircle, AlertCircle, Clock, ShieldAlert } from 'lucide-react';

interface RouteTableProps {
  decisions: RouteDecision[];
  policyVersion: string;
}

export const RouteTable: React.FC<RouteTableProps> = ({ decisions, policyVersion }) => {
  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'SELECTED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> SELECTED
          </span>
        );
      case 'BELOW_THRESHOLD':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            <AlertCircle className="w-3.5 h-3.5 mr-1" /> BELOW THRESHOLD
          </span>
        );
      case 'DEFERRED_CAP':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950 text-purple-400 border border-purple-800">
            <Clock className="w-3.5 h-3.5 mr-1" /> DEFERRED (CAP)
          </span>
        );
      case 'EXCLUDED_SELF':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <XCircle className="w-3.5 h-3.5 mr-1" /> EXCLUDED (AUTHOR)
          </span>
        );
      case 'EXCLUDED_TOPIC':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
            <ShieldAlert className="w-3.5 h-3.5 mr-1" /> MUTED TOPIC
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {decision}
          </span>
        );
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 shadow-xl">
      <table className="w-full text-left text-sm text-slate-200">
        <thead className="bg-slate-800/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-700">
          <tr>
            <th className="py-3 px-4">Candidate Agent</th>
            <th className="py-3 px-3 text-center">Dense D (65%)</th>
            <th className="py-3 px-3 text-center">Topic T (20%)</th>
            <th className="py-3 px-3 text-center">Business B (15%)</th>
            <th className="py-3 px-3 text-center font-bold text-sky-400">Composite S</th>
            <th className="py-3 px-3 text-center">Cutoff</th>
            <th className="py-3 px-4 text-center">Decision</th>
            <th className="py-3 px-4">Evidence & Arithmetic</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 font-mono text-xs">
          {decisions.map((d) => (
            <tr key={d.agent_id} className="hover:bg-slate-800/40 transition">
              <td className="py-3.5 px-4 font-sans font-medium text-slate-100">
                {d.agent_name}
              </td>

              <td className="py-3.5 px-3 text-center text-slate-300">
                {d.dense_score !== null ? d.dense_score.toFixed(4) : <span className="text-slate-600">--</span>}
              </td>

              <td className="py-3.5 px-3 text-center text-slate-300">
                {d.topic_score !== null ? d.topic_score.toFixed(4) : <span className="text-slate-600">--</span>}
              </td>

              <td className="py-3.5 px-3 text-center text-slate-300">
                {d.compatibility_score !== null ? d.compatibility_score.toFixed(4) : <span className="text-slate-600">--</span>}
              </td>

              <td className="py-3.5 px-3 text-center font-bold text-sky-300">
                {d.final_score !== null ? d.final_score.toFixed(4) : <span className="text-slate-600">--</span>}
              </td>

              <td className="py-3.5 px-3 text-center text-slate-400">
                {d.threshold.toFixed(2)}
              </td>

              <td className="py-3.5 px-4 text-center font-sans">
                {getDecisionBadge(d.decision)}
              </td>

              <td className="py-3.5 px-4 font-sans text-xs text-slate-400 max-w-md">
                {d.evidence}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

