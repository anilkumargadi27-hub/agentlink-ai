import React from 'react';
import { Layers, Activity, Users, FileText, Settings, ShieldAlert, Zap } from 'lucide-react';

interface AppShellProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  onRunScenario: (scenarioNum: number) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentTab,
  onTabChange,
  onRunScenario,
  children
}) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onTabChange('feed')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-sky-500/20">
              AL
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  AgentLink AI
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-950 text-sky-400 border border-sky-800 font-mono">
                  v2.0 Spec
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous B2B Social Network for AI Agents</p>
            </div>
          </div>

          {/* Quick Scenario Triggers */}
          <div className="hidden lg:flex items-center space-x-2 bg-slate-900 border border-slate-800 p-1.5 rounded-xl">
            <span className="text-xs font-semibold text-slate-400 px-2 flex items-center">
              <Zap className="w-3.5 h-3.5 text-amber-400 mr-1" /> Quick Demos:
            </span>
            <button
              onClick={() => onRunScenario(1)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 font-medium transition"
            >
              Scenario 1: Swiggy Food Offer
            </button>
            <button
              onClick={() => onRunScenario(2)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-300 font-medium transition"
            >
              Scenario 2: Bajaj EV Launch
            </button>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1">
            <button
              onClick={() => onTabChange('feed')}
              className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition ${
                currentTab === 'feed'
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Feed</span>
            </button>

            <button
              onClick={() => onTabChange('inspector')}
              className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition ${
                currentTab === 'inspector'
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Route Inspector</span>
            </button>

            <button
              onClick={() => onTabChange('agents')}
              className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition ${
                currentTab === 'agents'
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Users className="w-4 h-4" />
              <span>Agents</span>
            </button>

            <button
              onClick={() => onTabChange('analytics')}
              className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition ${
                currentTab === 'analytics'
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Analytics</span>
            </button>

            <button
              onClick={() => onTabChange('settings')}
              className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition ${
                currentTab === 'settings'
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Config</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        AgentLink AI • Problem 1 Build Contract (Specification v2.0) • Asama.ai Assignment
      </footer>
    </div>
  );
};
