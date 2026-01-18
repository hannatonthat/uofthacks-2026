'use client';

import { useEffect, useState } from 'react';

interface AgentStats {
  total: number;
  satisfaction: number;
}

interface AIInsights {
  issues: string[];
  recommendation: string;
  confidence: number;
}

interface AnalyticsSummary {
  total_ratings: number;
  overall_satisfaction: number;
  agent_breakdown: Record<string, AgentStats>;
  recent_improvements: any[];
  ai_insights?: AIInsights;
}

interface RatingStats {
  _id: string;
  total_ratings: number;
  positive_ratings: number;
  negative_ratings: number;
  avg_rating: number;
}

export default function AnalyticsDashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [ratingStats, setRatingStats] = useState<RatingStats[]>([]);
  const [loading, setLoading] = useState(true);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchAnalytics();
    // Refresh every 10 seconds
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchAnalytics = async () => {
    try {
      // Fetch rating stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/ratings/stats`);
      const statsData = await statsResponse.json();
      setRatingStats(statsData.stats || []);
      
      // Fetch AI-powered analytics summary
      const summaryResponse = await fetch(`${API_BASE_URL}/api/analytics/summary`);
      const summaryData = await summaryResponse.json();
      
      if (summaryData.summary) {
        setSummary(summaryData.summary);
      } else {
        // Fallback: Build summary from stats
        if (statsData.stats && statsData.stats.length > 0) {
          const totalRatings = statsData.stats.reduce((sum: number, s: RatingStats) => sum + s.total_ratings, 0);
          const totalPositive = statsData.stats.reduce((sum: number, s: RatingStats) => sum + s.positive_ratings, 0);
          const overallSat = totalRatings > 0 ? (totalPositive / totalRatings) * 100 : 0;
          
          const breakdown: Record<string, AgentStats> = {};
          statsData.stats.forEach((stat: RatingStats) => {
            breakdown[stat._id] = {
              total: stat.total_ratings,
              satisfaction: stat.total_ratings > 0 ? (stat.positive_ratings / stat.total_ratings) * 100 : 0
            };
          });
          
          setSummary({
            total_ratings: totalRatings,
            overall_satisfaction: overallSat,
            agent_breakdown: breakdown,
            recent_improvements: []
          });
        }
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      setLoading(false);
    }
  };

  const getAgentName = (agentType: string) => {
    const names: Record<string, string> = {
      sustainability: 'Sustainability',
      indigenous: 'Indigenous Context',
      proposal: 'Proposal Workflow'
    };
    return names[agentType] || agentType;
  };

  const getSatisfactionColor = (satisfaction: number) => {
    if (satisfaction >= 70) return 'text-green-400';
    if (satisfaction >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getSatisfactionBg = (satisfaction: number) => {
    if (satisfaction >= 70) return 'bg-green-500';
    if (satisfaction >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <div>
              <h1 className="text-4xl font-bold">Analytics Dashboard</h1>
            </div>
            <div className="flex gap-3">
              <a 
                href="/insights"
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold"
              >
                <span>🎯</span>
                Your Insights
              </a>
              <a 
                href="/"
                className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold"
              >
                <span>←</span>
                Back to Map
              </a>
            </div>
          </div>
          <p className="text-gray-400">Real-time AI agent performance and personalization insights</p>
        </div>

        {/* Overall Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Total Ratings</div>
            <div className="text-3xl font-bold">{summary?.total_ratings || 0}</div>
            <div className="text-gray-500 text-xs mt-1">All agents combined</div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Overall Satisfaction</div>
            <div className={`text-3xl font-bold ${getSatisfactionColor(summary?.overall_satisfaction || 0)}`}>
              {(summary?.overall_satisfaction || 0).toFixed(1)}%
            </div>
            <div className="text-gray-500 text-xs mt-1">Positive feedback rate</div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Active Agents</div>
            <div className="text-3xl font-bold">{Object.keys(summary?.agent_breakdown || {}).length}</div>
            <div className="text-gray-500 text-xs mt-1">Agents receiving feedback</div>
          </div>
        </div>

        {/* Agent Breakdown */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
          <h2 className="text-2xl font-bold mb-6">Agent Performance</h2>
          
          {ratingStats.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">No ratings yet</p>
              <p className="text-sm">Start using the agents and provide feedback to see analytics</p>
            </div>
          ) : (
            <div className="space-y-6">
              {ratingStats.map((stat) => {
                const satisfaction = stat.total_ratings > 0 
                  ? (stat.positive_ratings / stat.total_ratings) * 100 
                  : 0;
                
                return (
                  <div key={stat._id} className="border-b border-gray-700 pb-6 last:border-b-0 last:pb-0">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-xl font-semibold">{getAgentName(stat._id)}</h3>
                        <p className="text-gray-400 text-sm">{stat.total_ratings} total ratings</p>
                      </div>
                      <div className={`text-2xl font-bold ${getSatisfactionColor(satisfaction)}`}>
                        {satisfaction.toFixed(1)}%
                      </div>
                    </div>
                    
                    {/* Progress bar */}
                    <div className="w-full bg-gray-700 rounded-full h-3 mb-2">
                      <div 
                        className={`${getSatisfactionBg(satisfaction)} h-3 rounded-full transition-all duration-500`}
                        style={{ width: `${satisfaction}%` }}
                      ></div>
                    </div>
                    
                    {/* Rating breakdown */}
                    <div className="flex gap-4 text-sm">
                      <span className="text-green-400">
                        👍 {stat.positive_ratings} positive
                      </span>
                      <span className="text-red-400">
                        👎 {stat.negative_ratings} negative
                      </span>
                      <span className="text-gray-500">
                        Avg: {stat.avg_rating.toFixed(2)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* AI Insights Box (if available) */}
        {summary?.ai_insights && (
          <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-lg p-6 border border-purple-500/50 mb-8">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
              <span className="text-2xl">🧠</span>
              Live AI Analysis
            </h2>
            
            <div className="space-y-4">
              <div className="bg-black/30 rounded-lg p-4">
                <div className="text-sm font-semibold text-purple-300 mb-2">Issues Detected by AI:</div>
                <div className="flex flex-wrap gap-2">
                  {summary.ai_insights.issues.map((issue, i) => (
                    <span key={i} className="bg-red-500/20 text-red-300 px-3 py-1 rounded-full text-sm">
                      ⚠️ {issue}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="bg-black/30 rounded-lg p-4">
                <div className="text-sm font-semibold text-green-300 mb-2">AI's Recommendation:</div>
                <p className="text-gray-200">{summary.ai_insights.recommendation}</p>
              </div>
              
              <div className="bg-black/30 rounded-lg p-4">
                <div className="text-sm font-semibold text-blue-300 mb-2">Confidence:</div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-700 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-green-500 h-3 rounded-full"
                      style={{ width: `${summary.ai_insights.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xl font-bold text-blue-400">
                    {(summary.ai_insights.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  AI's confidence in this analysis based on data quality and pattern clarity
                </p>
              </div>
            </div>
          </div>
        )}

        {/* AI Personalization in Action */}
        <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg p-6 border border-blue-700/50 mb-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            How AI Personalization Works
          </h2>
          
          <div className="space-y-4">
            <div className="bg-gray-800/50 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-blue-400">Data → Insights → Action Loop</h3>
              <ol className="space-y-2 text-sm text-gray-300">
                <li className="flex gap-2">
                  <span className="text-blue-400 font-bold">1.</span>
                  <span><strong>Data:</strong> Users rate agent responses with 👍/👎 buttons</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-blue-400 font-bold">2.</span>
                  <span><strong>Insights:</strong> AnalyticsAgent detects patterns (e.g., "responses too technical")</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-blue-400 font-bold">3.</span>
                  <span><strong>Action:</strong> AI automatically adapts future responses to be simpler</span>
                </li>
              </ol>
            </div>

            <div className="bg-gray-800/50 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-purple-400">Beyond Rules-Based Logic</h3>
              <p className="text-sm text-gray-300 mb-2">
                This isn't just "if rating &lt; 3 then simplify" - the AI analyzes:
              </p>
              <ul className="space-y-1 text-sm text-gray-300 list-disc list-inside">
                <li>Response length patterns in negative feedback</li>
                <li>Technical language usage correlations</li>
                <li>Context and user behavior clustering</li>
                <li>Generates custom prompts using LLM analysis</li>
              </ul>
            </div>

            <div className="bg-gray-800/50 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-green-400">Self-Improving Product</h3>
              <p className="text-sm text-gray-300">
                As users interact and provide feedback, the agents literally get better. 
                Same question asked twice → better response the second time based on aggregate learning.
              </p>
            </div>
          </div>
        </div>

        {/* Features Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span>📊</span>
              Adaptive Agent Responses
            </h3>
            <p className="text-sm text-gray-400 mb-3">
              Agents query rating history before responding and adjust their tone, length, and complexity based on what worked for similar queries.
            </p>
            <div className="text-xs text-blue-400 font-mono">
              analytics.get_rating_insights() → personalization_prompt
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span>🎯</span>
              Personalized Workflows
            </h3>
            <p className="text-sm text-gray-400 mb-3">
              Proposal workflows adapt based on user completion patterns. Steps that are commonly skipped get simplified or reordered.
            </p>
            <div className="text-xs text-blue-400 font-mono">
              analytics.get_workflow_insights() → adaptive_steps
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span>💡</span>
              Proactive Guidance
            </h3>
            <p className="text-sm text-gray-400 mb-3">
              System detects when users are stuck (repeated negative feedback) and automatically offers helpful suggestions.
            </p>
            <div className="text-xs text-blue-400 font-mono">
              analytics.detect_stuck_user() → proactive_help
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span>🔄</span>
              Smart Agent Routing
            </h3>
            <p className="text-sm text-gray-400 mb-3">
              AI analyzes which agents work best for different query types and suggests switches when appropriate.
            </p>
            <div className="text-xs text-blue-400 font-mono">
              analytics.get_user_preferences() → agent_suggestions
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
