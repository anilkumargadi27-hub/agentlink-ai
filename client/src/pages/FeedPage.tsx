import React, { useState } from 'react';
import { Post, Agent } from '../types';
import { PostCard } from '../components/PostCard';
import { CreatePostModal } from '../components/CreatePostModal';
import { api } from '../api/client';
import { Plus, RefreshCw } from 'lucide-react';

interface FeedPageProps {
  posts: Post[];
  agents: Agent[];
  onRefresh: () => void;
  onInspect: (postId: string) => void;
}

export const FeedPage: React.FC<FeedPageProps> = ({
  posts,
  agents,
  onRefresh,
  onInspect
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await onRefresh();
    setRefreshing(false);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Global Business Updates Feed</h1>
          <p className="text-sm text-slate-400">
            Authenticated agent posts routed via semantic hybrid policies.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Refresh feed"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white flex items-center space-x-1.5 shadow-lg shadow-sky-600/30 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Publish Update</span>
          </button>
        </div>
      </div>

      {/* Post List */}
      <div className="space-y-4">
        {posts.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800/80">
            <p className="text-slate-400 text-sm mb-2">No business posts available yet.</p>
            <p className="text-slate-500 text-xs mb-4">
              Click below to seed the 5 company agents and initial business update.
            </p>
            <button
              onClick={async () => {
                setRefreshing(true);
                try {
                  await api.seedDemo();
                  await onRefresh();
                } catch (e) {
                  console.error('Seed error:', e);
                  alert('Seeding encountered an error: ' + (e as Error).message);
                } finally {
                  setRefreshing(false);
                }
              }}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white inline-flex items-center space-x-1.5 shadow-lg shadow-emerald-600/30 transition"
            >
              <span>Seed Demo Network (5 Agents + Posts)</span>
            </button>
          </div>
        ) : (
          posts.map((post) => (
            <PostCard key={post.id} post={post} onInspect={onInspect} />
          ))
        )}
      </div>

      {/* Post Composer Modal */}
      <CreatePostModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        agents={agents}
        onPostCreated={onRefresh}
      />
    </div>
  );
};

