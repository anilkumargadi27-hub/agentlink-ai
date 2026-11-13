import React, { useState } from 'react';
import { Agent } from '../types';
import { api } from '../api/client';
import { Users, Shield, Tag, Ban, Sliders, ToggleLeft, ToggleRight, Play, Pause, Loader2 } from 'lucide-react';

interface AgentsPageProps {
  agents: Agent[];
  onRefresh?: () => void;
}

export const AgentsPage: React.FC<AgentsPageProps> = ({ agents, onRefresh }) => {
  const [togglingAgentId, setTogglingAgentId] = useState<string | null>(null);

  const handleToggleActive = async (ag: Agent) => {
    try {
      setTogglingAgentId(ag.id);
      await api.updateAgent(ag.id, { active: !ag.active });
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to toggle agent active state:', err);
    } finally {
      setTogglingAgentId(null);
    }
  };

  const handleToggleMode = async (ag: Agent) => {
    if (!ag.subscription) return;
    const newMode = ag.subscription.response_mode === 'AUTO' ? 'PAUSED' : 'AUTO';
    try {
      setTogglingAgentId(ag.id);
      await api.updateAgentSubscription(ag.id, {
        interest_text: ag.subscription.interest_text,
        include_topics: ag.subscription.include_topics,
        exclude_topics: ag.subscription.exclude_topics,
        response_mode: newMode,
        threshold: ag.subscription.threshold
      });
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to toggle response mode:', err);
    } finally {
      setTogglingAgentId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Users className="w-6 h-6 text-sky-400" />
          <h1 className="text-2xl font-bold text-slate-100">Registered Company Agents</h1>
        </div>
        <p className="text-sm text-slate-400">
          Independent participant profiles, semantic interests, hard topic exclusions, and response settings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map((ag) => {
          const isBusy = togglingAgentId === ag.id;

          return (
            <div
              key={ag.id}
              className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4 transition hover:border-slate-700"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-base font-bold text-slate-100">{ag.company_name}</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-950 text-sky-400 border border-sky-800 font-mono font-semibold flex items-center">
                      <Shield className="w-3 h-3 mr-1" /> {ag.verification_status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{ag.description}</p>
                </div>

                {/* Interactive Active / Inactive Toggle Button */}
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => handleToggleActive(ag)}
                  title={`Click to ${ag.active ? 'deactivate' : 'activate'} this agent`}
                  className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold border transition shadow-sm ${
                    ag.active
                      ? 'bg-emerald-950/90 text-emerald-300 border-emerald-700/80 hover:bg-emerald-900'
                      : 'bg-rose-950/90 text-rose-300 border-rose-700/80 hover:bg-rose-900'
                  } disabled:opacity-50`}
                >
                  {isBusy ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : ag.active ? (
                    <ToggleRight className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <ToggleLeft className="w-4 h-4 text-rose-400" />
                  )}
                  <span>{ag.active ? 'Active' : 'Inactive'}</span>
                </button>
              </div>

              {ag.subscription && (
                <div className="space-y-3 pt-3 border-t border-slate-800/80 text-xs">
                  <div>
                    <span className="text-slate-500 font-medium block mb-1">Declared Interests:</span>
                    <p className="text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 leading-relaxed font-mono text-[11px]">
                      {ag.subscription.interest_text}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-slate-500 font-medium flex items-center mb-1">
                        <Tag className="w-3 h-3 mr-1 text-sky-400" /> Include Topics:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {ag.subscription.include_topics.length > 0 ? (
                          ag.subscription.include_topics.map((t) => (
                            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-600 italic">None</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-500 font-medium flex items-center mb-1">
                        <Ban className="w-3 h-3 mr-1 text-rose-400" /> Exclude Topics:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {ag.subscription.exclude_topics.length > 0 ? (
                          ag.subscription.exclude_topics.map((t) => (
                            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-900/60 font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-600 italic">None</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/40 text-[11px] text-slate-400">
                    <span className="flex items-center">
                      <Sliders className="w-3 h-3 mr-1 text-sky-400" /> Threshold: <b className="text-slate-200 ml-1">{ag.subscription.threshold}</b>
                    </span>

                    {/* Interactive Response Mode Toggle */}
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleToggleMode(ag)}
                      title="Click to toggle between AUTO and PAUSED autonomous responses"
                      className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-slate-200 transition"
                    >
                      {ag.subscription.response_mode === 'AUTO' ? (
                        <Play className="w-3 h-3 text-emerald-400 fill-emerald-400" />
                      ) : (
                        <Pause className="w-3 h-3 text-amber-400 fill-amber-400" />
                      )}
                      <span>Mode: <b className={ag.subscription.response_mode === 'AUTO' ? 'text-emerald-400' : 'text-amber-400'}>{ag.subscription.response_mode}</b></span>
                    </button>

                    <span>Profile v{ag.profile_version}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
