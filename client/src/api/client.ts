import { Post, Agent, Comment, RouteInspectorData, InboxItem, AnalyticsSummary } from '../types';

const API_BASE = '/api/v1';

export const api = {
  async getPosts(): Promise<Post[]> {
    const res = await fetch(`${API_BASE}/posts`);
    if (!res.ok) throw new Error('Failed to load posts');
    const data = await res.json();
    return data.data;
  },

  async getPostComments(postId: string): Promise<Comment[]> {
    const res = await fetch(`${API_BASE}/posts/${postId}/comments`);
    if (!res.ok) throw new Error('Failed to load comments');
    const data = await res.json();
    return data.data;
  },

  async publishPost(agentId: string, postData: any): Promise<any> {
    const res = await fetch(`${API_BASE}/agents/${agentId}/posts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': `web_${Date.now()}_${Math.random().toString(36).substring(7)}`
      },
      body: JSON.stringify(postData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Publishing failed');
    }
    return res.json();
  },

  async getPostRouting(postId: string): Promise<RouteInspectorData> {
    const res = await fetch(`${API_BASE}/posts/${postId}/routing`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Routing data not available yet');
    }
    return res.json();
  },

  async getAgents(): Promise<Agent[]> {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error('Failed to load agents');
    const data = await res.json();
    return data.data;
  },

  async updateAgent(agentId: string, data: { active?: boolean; description?: string }): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents/${agentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to update agent');
    return res.json();
  },

  async updateAgentSubscription(agentId: string, subData: any): Promise<any> {
    const res = await fetch(`${API_BASE}/agents/${agentId}/subscription`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subData)
    });
    if (!res.ok) throw new Error('Failed to update subscription');
    return res.json();
  },

  async getAnalytics(): Promise<AnalyticsSummary> {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    if (!res.ok) throw new Error('Failed to load analytics');
    return res.json();
  },

  async getHealth(): Promise<any> {
    const res = await fetch(`/health/ready`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async seedDemo(): Promise<any> {
    const res = await fetch(`${API_BASE}/seed`, { method: 'POST' });
    if (!res.ok) {
      // Fallback to GET /api/v1/seed
      const getRes = await fetch(`${API_BASE}/seed`);
      if (!getRes.ok) throw new Error('Failed to seed network');
      return getRes.json();
    }
    return res.json();
  }
};
