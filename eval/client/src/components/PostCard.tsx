import React, { useState } from 'react';
import { Post, Comment } from '../types';
import { api } from '../api/client';
import { MessageSquare, Layers, Clock, CheckCircle2, Bot, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

interface PostCardProps {
  post: Post;
  onInspect: (postId: string) => void;
}

export const PostCard: React.FC<PostCardProps> = ({ post, onInspect }) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [showComments, setShowComments] = useState(false);

  const toggleComments = async () => {
    if (!showComments && comments.length === 0) {
      setLoadingComments(true);
      try {
        const data = await api.getPostComments(post.id);
        setComments(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingComments(false);
      }
    }
    setShowComments(!showComments);
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg hover:border-slate-700 transition">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
            {post.author_name ? post.author_name[0] : 'A'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-100">{post.author_name}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {post.intent}
              </span>
            </div>
            <span className="text-xs text-slate-500">
              {new Date(post.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Routing Status Badge */}
        <div>
          {post.routing_state === 'ROUTED' ? (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Routed
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950 text-amber-400 border border-amber-800">
              <Clock className="w-3.5 h-3.5 mr-1 animate-spin" /> Routing...
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <h3 className="text-lg font-semibold text-slate-100 mb-2">{post.title}</h3>
      <p className="text-sm text-slate-300 leading-relaxed mb-4">{post.content}</p>

      {/* Topics */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {post.topics.map((t) => (
          <span
            key={t}
            className="text-xs font-mono px-2 py-0.5 rounded-md bg-slate-800/90 text-sky-400 border border-slate-700"
          >
            #{t}
          </span>
        ))}
      </div>

      {/* Footer Controls */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
        <button
          onClick={() => onInspect(post.id)}
          className="text-xs font-medium flex items-center space-x-1.5 text-sky-400 hover:text-sky-300 bg-sky-950/60 hover:bg-sky-900/60 px-3 py-1.5 rounded-lg border border-sky-800/60 transition"
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Inspect Routing Decisions</span>
        </button>

        <button
          onClick={toggleComments}
          className="text-xs font-medium flex items-center space-x-1 text-slate-400 hover:text-slate-200 transition"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>{post.comment_count} Responses</span>
          {showComments ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
        </button>
      </div>

      {/* Expandable Comments Section */}
      {showComments && (
        <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-2">
            <span className="flex items-center">
              <Bot className="w-3.5 h-3.5 mr-1 text-sky-400" /> Autonomous Agent Responses
            </span>
            <span className="text-slate-500">LLM Grounded</span>
          </div>

          {loadingComments ? (
            <div className="text-center py-4 text-xs text-slate-500">Loading verified comments...</div>
          ) : comments.length === 0 ? (
            <div className="text-center py-3 text-xs text-slate-500 bg-slate-950/40 rounded-lg">
              No public comments posted for this notification.
            </div>
          ) : (
            comments.map((c) => (
              <div
                key={c.id}
                className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-3.5 shadow-sm"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-xs text-slate-200">{c.author_name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 flex items-center">
                      <Sparkles className="w-2.5 h-2.5 mr-1" /> {c.generation_mode}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(c.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-sans">{c.content}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
