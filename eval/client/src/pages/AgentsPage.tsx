import React from 'react';
import { Agent } from '../types';
import { Users, Shield, Tag, Ban, Sliders } from 'lucide-react';

interface AgentsPageProps {
  agents: Agent[];
}

export const AgentsPage: React.FC<AgentsPageProps> = ({ agents }) => {
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
        {agents.map((ag) => (
          <div
            key={ag.id}
            className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-slate-100">{ag.company_name}</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-950 text-sky-400 border border-sky-800 font-mono font-semibold flex items-center">
                    <Shield className="w-3 h-3 mr-1" /> {ag.verification_status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{ag.description}</p>
              </div>

              <span className={`text-xs px-2 py-0.5 rounded font-mono ${ag.active ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'}`}>
                {ag.active ? 'Active' : 'Inactive'}
              </span>
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
                    <Sliders className="w-3 h-3 mr-1" /> Threshold: <b className="text-slate-200 ml-1">{ag.subscription.threshold}</b>
                  </span>
                  <span>
                    Mode: <b className="text-sky-400">{ag.subscription.response_mode}</b>
                  </span>
                  <span>
                    Profile v{ag.profile_version}
                  </span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
