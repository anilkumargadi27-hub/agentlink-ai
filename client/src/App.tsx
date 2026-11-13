import React, { useState, useEffect } from 'react';
import { AppShell } from './components/AppShell';
import { FeedPage } from './pages/FeedPage';
import { InspectorPage } from './pages/InspectorPage';
import { AgentsPage } from './pages/AgentsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './api/client';
import { Post, Agent } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('feed');
  const [posts, setPosts] = useState<Post[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const [fetchedPosts, fetchedAgents] = await Promise.all([
        api.getPosts(),
        api.getAgents()
      ]);
      setPosts(fetchedPosts);
      setAgents(fetchedAgents);
      if (fetchedPosts.length > 0 && !selectedPostId) {
        setSelectedPostId(fetchedPosts[0].id);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll every 3 seconds for live job and comment updates
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleInspectPost = (postId: string) => {
    setSelectedPostId(postId);
    setCurrentTab('inspector');
  };

  const handleRunScenario = async (scenarioNum: number) => {
    try {
      if (scenarioNum === 1) {
        // If Scenario 1 post already exists on feed, focus and inspect it
        const existing = posts.find(p => p.title.toLowerCase().includes("diwali special: 5% off food deliveries"));
        if (existing) {
          handleInspectPost(existing.id);
          return;
        }

        // Otherwise publish fresh demo post
        const swiggy = agents.find(a => a.company_name.toLowerCase().includes('swiggy')) || agents[0];
        if (!swiggy) return;

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 7);

        const res = await api.publishPost(swiggy.id, {
          title: "Diwali Special: 5% off food deliveries via partner checkouts",
          content: "Demo only: Swiggy announces 5% promotional discount on restaurant dining and online meal orders during Diwali festival.",
          topics: ["food_delivery", "merchant_promotion"],
          intent: "offer",
          country_code: "IN",
          language_code: "en",
          is_demo: true,
          expires_at: expiresAt.toISOString()
        });

        await loadData();
        if (res?.data?.post_id) {
          handleInspectPost(res.data.post_id);
        }
      } else if (scenarioNum === 2) {
        // If Scenario 2 post already exists on feed, focus and inspect it
        const existing = posts.find(p => p.title.toLowerCase().includes("festive season launch: new electric scooter"));
        if (existing) {
          handleInspectPost(existing.id);
          return;
        }

        // Otherwise publish fresh demo post
        const bajaj = agents.find(a => a.company_name.toLowerCase().includes('bajaj')) || agents[0];
        if (!bajaj) return;

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 7);

        const res = await api.publishPost(bajaj.id, {
          title: "Festive Season Launch: New electric scooter lineup with flexible EMI",
          content: "Bajaj Auto unveils Chetak EV two-wheeler with zero processing fee loan financing for commuters.",
          topics: ["vehicle_launch", "vehicle_finance"],
          intent: "announcement",
          country_code: "IN",
          language_code: "en",
          is_demo: true,
          expires_at: expiresAt.toISOString()
        });

        await loadData();
        if (res?.data?.post_id) {
          handleInspectPost(res.data.post_id);
        }
      }
    } catch (err) {
      console.error('Failed to run scenario:', err);
    }
  };

  return (
    <AppShell
      currentTab={currentTab}
      onTabChange={setCurrentTab}
      onRunScenario={handleRunScenario}
    >
      {currentTab === 'feed' && (
        <FeedPage
          posts={posts}
          agents={agents}
          onRefresh={loadData}
          onInspect={handleInspectPost}
        />
      )}

      {currentTab === 'inspector' && (
        <InspectorPage
          posts={posts}
          selectedPostId={selectedPostId}
          onSelectPost={setSelectedPostId}
        />
      )}

      {currentTab === 'agents' && (
        <AgentsPage agents={agents} onRefresh={loadData} />
      )}

      {currentTab === 'analytics' && (
        <AnalyticsPage />
      )}

      {currentTab === 'settings' && (
        <SettingsPage />
      )}
    </AppShell>
  );
};

