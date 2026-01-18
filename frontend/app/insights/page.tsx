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
  sustainability: '🌿 Sustainability',
  indigenous: '🪶 Indigenous Context',
  proposal: '📋 Proposal Workflow'
};

export default function InsightsPage() {
  const [insights, setInsights] = useState<UserInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [deviceId, setDeviceId] = useState<string>('');

  useEffect(() => {
    const userId = getDeviceId();
    setDeviceId(userId);
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
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Analyzing your behavior patterns...</p>
        </div>
      </div>
    );
  }

  if (!insights?.has_data) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-4">Your Personalized Insights</h1>
          
          <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg p-8 border border-blue-700/50 text-center">
            <div className="text-6xl mb-4">🎯</div>
            <h2 className="text-2xl font-bold mb-4">Start Your Journey!</h2>
            <p className="text-gray-300 mb-6">
              {insights?.message || 'Chat with our AI agents to unlock personalized insights about your interests and learning style.'}
            </p>
            <a 
              href="/"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
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
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Your Personalized Insights</h1>
          <p className="text-gray-400">AI-generated profile based on your behavior</p>
        </div>

        {/* Personality Type - Big Card */}
        <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-lg p-8 border border-purple-500/50 mb-6">
          <div className="flex items-start gap-6">
            <div className="text-8xl">{personalityInfo.emoji}</div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-purple-300 mb-1">YOUR PERSONALITY TYPE</div>
              <h2 className="text-4xl font-bold mb-3">{insights.personality_type}</h2>
              <p className="text-gray-200 text-lg leading-relaxed">{personalityInfo.description}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Stats Card */}
          <div className="bg-gradient-to-br from-blue-900/30 to-cyan-900/30 rounded-lg p-6 border border-blue-700/50">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>📊</span>
              Your Activity
            </h3>
            
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Total Interactions</div>
                <div className="text-3xl font-bold text-blue-400">{insights.total_interactions}</div>
              </div>
              
              <div>
                <div className="text-sm text-gray-400 mb-1">Satisfaction Rate</div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-700 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-green-500 to-blue-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${insights.satisfaction_rate}%` }}
                    ></div>
                  </div>
                  <span className="text-xl font-bold text-green-400">
                    {insights.satisfaction_rate?.toFixed(0)}%
                  </span>
                </div>
              </div>
              
              <div>
                <div className="text-sm text-gray-400 mb-1">Learning Style</div>
                <div className="text-lg font-semibold text-cyan-400 capitalize">
                  {insights.learning_style}
                </div>
              </div>
            </div>
          </div>

          {/* Agent Usage Card */}
          <div className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 rounded-lg p-6 border border-green-700/50">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>🤖</span>
              Agent Preferences
            </h3>
            
            {insights.favorite_agent && (
              <div className="mb-4 bg-green-900/30 rounded-lg p-3 border border-green-700/50">
                <div className="text-sm text-gray-400 mb-1">Most Used</div>
                <div className="text-xl font-bold text-green-400">
                  {AGENT_NAMES[insights.favorite_agent] || insights.favorite_agent}
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              {Object.entries(insights.agent_usage || {}).map(([agent, count]) => {
                const total = Object.values(insights.agent_usage || {}).reduce((a, b) => a + b, 0);
                const percentage = total > 0 ? (count / total) * 100 : 0;
                
                return (
                  <div key={agent}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300">{AGENT_NAMES[agent] || agent}</span>
                      <span className="text-gray-400">{count} times</span>
                    </div>
                    <div className="bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all duration-500"
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
        <div className="bg-gradient-to-br from-orange-900/30 to-yellow-900/30 rounded-lg p-6 border border-orange-700/50 mb-6">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>💪</span>
            Your Strengths
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {insights.strengths?.map((strength, index) => (
              <div 
                key={index}
                className="bg-gradient-to-br from-orange-800/20 to-yellow-800/20 rounded-lg p-4 border border-orange-600/30"
              >
                <div className="text-3xl mb-2">
                  {['⭐', '🎯', '✨'][index % 3]}
                </div>
                <p className="text-gray-200">{strength}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Behavioral Patterns */}
        {insights.patterns && insights.patterns.length > 0 && (
          <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 rounded-lg p-6 border border-indigo-700/50 mb-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>🔍</span>
              Detected Patterns
            </h3>
            
            <div className="space-y-2">
              {insights.patterns.map((pattern, index) => (
                <div 
                  key={index}
                  className="bg-indigo-900/20 rounded-lg p-3 border border-indigo-700/30 flex items-center gap-3"
                >
                  <span className="text-2xl">📈</span>
                  <p className="text-gray-200">{pattern}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations Card */}
        <div className="bg-gradient-to-br from-pink-900/30 to-rose-900/30 rounded-lg p-6 border border-pink-700/50">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>💡</span>
            Personalized Recommendations
          </h3>
          
          <div className="space-y-3">
            {insights.recommendations?.map((rec, index) => (
              <div 
                key={index}
                className="bg-pink-900/20 rounded-lg p-4 border border-pink-700/30 flex items-start gap-3"
              >
                <span className="text-2xl">{['🎯', '🚀', '✨'][index % 3]}</span>
                <p className="text-gray-200 flex-1">{rec}</p>
              </div>
            ))}
          </div>
        </div>

        {/* How This Works */}
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-lg p-6 border border-gray-700/50 mt-6">
          <h3 className="text-xl font-bold mb-3 flex items-center gap-2">
            <span>🧠</span>
            How We Generated These Insights
          </h3>
          
          <p className="text-gray-300 mb-4">
            Our AI analyzed your complete behavioral history - every interaction, rating, and preference - 
            to create this personalized profile. This is the power of AI on data: turning your behavior 
            into actionable insights.
          </p>
          
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>🔒</span>
            <span>Your data stays anonymous. Device ID: {deviceId.substring(0, 16)}...</span>
          </div>
        </div>

        {/* Back Button */}
        <div className="mt-8 text-center">
          <a 
            href="/"
            className="inline-block bg-gray-700 hover:bg-gray-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
          >
            ← Back to Map
          </a>
        </div>
      </div>
    </div>
  );
}
