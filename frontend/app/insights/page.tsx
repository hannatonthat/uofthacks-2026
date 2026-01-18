'use client';

import { useEffect, useState } from 'react';
import { getDeviceId } from '@/lib/amplitude';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UserInsights {
  has_data: boolean;
  message?: string;
  total_interactions?: number;
  satisfaction_rate?: number;
  personality_type?: string;
  strengths?: string[];
  learning_style?: string;
  recommendations?: string[];
  favorite_agent?: string;
  agent_usage?: Record<string, number>;
  patterns?: string[];
}

const PERSONALITY_DESCRIPTIONS: Record<string, { emoji: string; description: string }> = {
  Explorer: {
    emoji: '🧭',
    description: 'You love discovering new information and exploring different perspectives. You ask curious questions and engage deeply with diverse content.'
  },
  Analyst: {
    emoji: '📊',
    description: 'You appreciate detailed, data-driven insights. You prefer thorough analysis and evidence-based recommendations.'
  },
  Builder: {
    emoji: '🏗️',
    description: 'You\'re action-oriented and focused on practical outcomes. You want concrete steps and actionable advice.'
  },
  Learner: {
    emoji: '📚',
    description: 'You value understanding and education. You engage thoughtfully and seek to deepen your knowledge systematically.'
  },
  Advocate: {
    emoji: '🌱',
    description: 'You care deeply about sustainability and indigenous perspectives. You\'re passionate about creating positive change.'
  }
};

const AGENT_NAMES: Record<string, string> = {
  sustainability: 'Sustainability',
  indigenous: 'Indigenous Context',
  proposal: 'Proposal Workflow'
};

export default function InsightsPage() {
  const [insights, setInsights] = useState<UserInsights | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const userId = getDeviceId();
    fetchInsights(userId);
  }, []);

  const fetchInsights = async (userId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analytics/user-insights/${userId}`);
      const data = await response.json();
      
      if (data.insights) {
        setInsights(data.insights);
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch user insights:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto mb-2"></div>
          <p className="text-stone-400 text-xs">Analyzing...</p>
        </div>
      </div>
    );
  }

  if (!insights?.has_data) {
    return (
      <div className="min-h-screen bg-black text-white p-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold mb-4">Insights</h1>
          
          <div className="bg-stone-900 rounded-lg p-4 border border-stone-800 text-center">
            <div className="text-4xl mb-2">🎯</div>
            <h2 className="text-lg font-bold mb-2">Start Your Journey</h2>
            <p className="text-stone-300 mb-3 text-xs">
              {insights?.message || 'Chat with our agents to unlock insights.'}
            </p>
            <a 
              href="/"
              className="inline-block bg-stone-800 hover:bg-stone-700 text-white font-semibold px-6 py-2 rounded-lg transition-colors text-xs"
            >
              Explore the Map
            </a>
          </div>
        </div>
      </div>
    );
  }

  const personalityInfo = PERSONALITY_DESCRIPTIONS[insights.personality_type || 'Explorer'];

  return (
    <div className="min-h-screen bg-black text-white p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold mb-0.5">Insights</h1>
          <p className="text-stone-400 text-xs">Profile based on your behavior</p>
        </div>

        {/* Personality Type - Big Card */}
        <div className="bg-stone-900 rounded-lg p-4 border border-stone-800 mb-3">
          <div className="flex items-start gap-3">
            <div className="text-4xl">{personalityInfo.emoji}</div>
            <div className="flex-1">
              <div className="text-xs font-semibold text-stone-400 mb-0.5">PERSONALITY TYPE</div>
              <h2 className="text-xl font-bold mb-1">{insights.personality_type}</h2>
              <p className="text-stone-300 text-xs leading-relaxed">{personalityInfo.description}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          {/* Stats Card */}
          <div className="bg-stone-900 rounded-lg p-3 border border-stone-800">
            <h3 className="text-sm font-bold mb-2">Activity</h3>
            
            <div className="space-y-2">
              <div>
                <div className="text-xs text-stone-400 mb-0.5">Interactions</div>
                <div className="text-xl font-bold text-emerald-400">{insights.total_interactions}</div>
              </div>
              
              <div>
                <div className="text-xs text-stone-400 mb-1">Satisfaction</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-stone-800 rounded-full h-1.5">
                    <div 
                      className="bg-sky-400 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${insights.satisfaction_rate}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-bold text-sky-400">
                    {insights.satisfaction_rate?.toFixed(0)}%
                  </span>
                </div>
              </div>
              
              <div>
                <div className="text-xs text-stone-400 mb-0.5">Learning Style</div>
                <div className="text-sm font-semibold text-amber-400 capitalize">
                  {insights.learning_style}
                </div>
              </div>
            </div>
          </div>

          {/* Agent Usage Card */}
          <div className="bg-stone-900 rounded-lg p-3 border border-stone-800">
            <h3 className="text-sm font-bold mb-2">Agents</h3>
            
            {insights.favorite_agent && (
              <div className="mb-2 bg-stone-800 rounded-lg p-2 border border-stone-700">
                <div className="text-xs text-stone-400 mb-0.5">Most Used</div>
                <div className="text-sm font-bold text-rose-400">
                  {AGENT_NAMES[insights.favorite_agent] || insights.favorite_agent}
                </div>
              </div>
            )}
            
            <div className="space-y-1.5">
              {Object.entries(insights.agent_usage || {}).map(([agent, count]) => {
                const total = Object.values(insights.agent_usage || {}).reduce((a, b) => a + b, 0);
                const percentage = total > 0 ? (count / total) * 100 : 0;
                
                return (
                  <div key={agent}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-stone-300">{AGENT_NAMES[agent] || agent}</span>
                      <span className="text-stone-400">{count}</span>
                    </div>
                    <div className="bg-stone-800 rounded-full h-1.5">
                      <div 
                        className="bg-emerald-400 h-1.5 rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Strengths Card */}
        <div className="bg-stone-900 rounded-lg p-3 border border-stone-800 mb-3">
          <h3 className="text-sm font-bold mb-2">Strengths</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {insights.strengths?.map((strength, index) => (
              <div 
                key={index}
                className="bg-stone-800 rounded-lg p-2 border border-stone-700"
              >
                <p className="text-stone-200 text-xs">{strength}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Behavioral Patterns */}
        {insights.patterns && insights.patterns.length > 0 && (
          <div className="bg-stone-900 rounded-lg p-3 border border-stone-800 mb-3">
            <h3 className="text-sm font-bold mb-2">Patterns</h3>
            
            <div className="space-y-1.5">
              {insights.patterns.map((pattern, index) => (
                <div 
                  key={index}
                  className="bg-stone-800 rounded-lg p-2 border border-stone-700"
                >
                  <p className="text-stone-200 text-xs">{pattern}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations Card */}
        <div className="bg-stone-900 rounded-lg p-3 border border-stone-800">
          <h3 className="text-sm font-bold mb-2">Recommendations</h3>
          
          <div className="space-y-1.5">
            {insights.recommendations?.map((rec, index) => (
              <div 
                key={index}
                className="bg-stone-800 rounded-lg p-2 border border-stone-700"
              >
                <p className="text-stone-200 text-xs flex-1">{rec}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Back Button */}
        <div className="mt-4 text-center">
          <a 
            href="/"
            className="inline-block bg-stone-800 hover:bg-stone-700 text-white font-semibold px-6 py-2 rounded-lg transition-colors text-xs"
          >
            ← Back to Map
          </a>
        </div>
      </div>
    </div>
  );
}
