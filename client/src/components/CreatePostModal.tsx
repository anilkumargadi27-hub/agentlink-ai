import React, { useState, useEffect } from 'react';
import { Agent } from '../types';
import { api } from '../api/client';
import { X, Send, Sparkles, AlertCircle, Check } from 'lucide-react';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  agents: Agent[];
  onPostCreated: () => void;
}

export const CreatePostModal: React.FC<CreatePostModalProps> = ({
  isOpen,
  onClose,
  agents,
  onPostCreated
}) => {
  const [authorId, setAuthorId] = useState(agents[0]?.id || '');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [topicsStr, setTopicsStr] = useState('');
  const [intent, setIntent] = useState('offer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Synchronize authorId whenever agents load or modal opens
  useEffect(() => {
    if (agents.length > 0) {
      if (!authorId || !agents.some(a => a.id === authorId)) {
        setAuthorId(agents[0].id);
      }
    }
  }, [agents, isOpen]);

  if (!isOpen) return null;

  const handleApplyPreset = (scenarioNum: number) => {
    if (scenarioNum === 1) {
      const swiggy = agents.find(a => a.company_name.toLowerCase().includes('swiggy')) || agents[0];
      if (swiggy) setAuthorId(swiggy.id);
      setTitle("Diwali Special: 5% off food deliveries via partner checkouts");
      setContent("Demo only: Swiggy announces 5% promotional discount on restaurant dining and online meal orders during Diwali festival.");
      setTopicsStr("food_delivery, merchant_promotion");
      setIntent("offer");
    } else if (scenarioNum === 2) {
      const bajaj = agents.find(a => a.company_name.toLowerCase().includes('bajaj')) || agents[0];
      if (bajaj) setAuthorId(bajaj.id);
      setTitle("Festive Season Launch: New electric scooter lineup with flexible EMI");
      setContent("Bajaj Auto unveils Chetak EV two-wheeler with zero processing fee loan financing for commuters.");
      setTopicsStr("vehicle_launch, vehicle_finance");
      setIntent("announcement");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authorId || !title || !content) {
      setError("Please select an agent and fill in title and content.");
      return;
    }

    setLoading(true);
    setError(null);

    const topics = topicsStr
      .split(',')
      .map(t => t.trim().toLowerCase())
      .filter(t => t.length > 0);

    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7);

    try {
      await api.publishPost(authorId, {
        title,
        content,
        topics,
        intent,
        country_code: "IN",
        language_code: "en",
        is_demo: true,
        expires_at: expiresAt.toISOString()
      });
      onPostCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to publish post');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-sky-400" />
            <h2 className="text-lg font-bold text-slate-100">Publish Business Update</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Preset scenario shortcuts */}
        <div className="my-4 p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
          <span className="text-xs font-semibold text-slate-400 block mb-2">Load Preset Demonstration:</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => handleApplyPreset(1)}
              className="text-xs px-2.5 py-1.5 rounded-lg bg-sky-950 text-sky-300 border border-sky-800/80 hover:bg-sky-900 transition flex-1 text-left"
            >
              🍔 Scenario 1: Food Delivery
            </button>
            <button
              type="button"
              onClick={() => handleApplyPreset(2)}
              className="text-xs px-2.5 py-1.5 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-800/80 hover:bg-emerald-900 transition flex-1 text-left"
            >
              ⚡ Scenario 2: Two-Wheeler EV
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center">
            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Publishing Agent Selection */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              Publishing Agent <span className="text-slate-500 font-normal">(Click an agent to toggle selection)</span>
            </label>

            {/* Interactive Toggle Pill Buttons */}
            {agents.length === 0 ? (
              <p className="text-xs text-amber-400 py-2">Loading agents from backend...</p>
            ) : (
              <>
                <div className="flex flex-wrap gap-2 mb-2.5">
                  {agents.map((ag) => {
                    const isSelected = authorId === ag.id;
                    return (
                      <button
                        key={ag.id}
                        type="button"
                        onClick={() => setAuthorId(ag.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition ${
                          isSelected
                            ? 'bg-sky-600 text-white border border-sky-400 shadow-md shadow-sky-600/30'
                            : 'bg-slate-950 text-slate-300 border border-slate-800 hover:border-slate-700 hover:text-white'
                        }`}
                      >
                        {isSelected && <Check className="w-3.5 h-3.5 mr-0.5" />}
                        <span>{ag.company_name}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Synchronized Dropdown */}
                <select
                  value={authorId}
                  onChange={(e) => setAuthorId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500 font-sans"
                >
                  {agents.map((ag) => (
                    <option key={ag.id} value={ag.id}>
                      {ag.company_name} ({ag.verification_status})
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Post Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Diwali festive cashback offer"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Content</label>
            <textarea
              rows={3}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Details of the commercial announcement or promotion..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Topics (comma separated)</label>
              <input
                type="text"
                value={topicsStr}
                onChange={(e) => setTopicsStr(e.target.value)}
                placeholder="food_delivery, merchant_promotion"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500 font-mono text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Intent</label>
              <select
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
              >
                <option value="offer">offer</option>
                <option value="announcement">announcement</option>
                <option value="market_update">market_update</option>
                <option value="partnership_request">partnership_request</option>
              </select>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white flex items-center space-x-1.5 shadow-lg shadow-sky-600/30 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{loading ? 'Submitting...' : 'Publish & Route'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
