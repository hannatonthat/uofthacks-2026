'use client';

import { useState, useEffect, useRef } from 'react';
import { createAgentChat, sendAgentMessage, ChatMessage, ChatResponse } from '@/lib/api';

interface AgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  panoramaPath: string | null;
  locationData: {
    lat: number;
    lon: number;
    address: string;
    territory?: string;
  } | null;
}

type AgentType = 'sustainability' | 'indigenous' | 'proposal';

interface AgentThread {
  threadId: string;
  messages: ChatMessage[];
  loading: boolean;
}

export default function AgentModal({ isOpen, onClose, panoramaPath, locationData }: AgentModalProps) {
  const [activeAgent, setActiveAgent] = useState<AgentType>('sustainability');
  const [threads, setThreads] = useState<Record<AgentType, AgentThread>>({
    sustainability: { threadId: '', messages: [], loading: false },
    indigenous: { threadId: '', messages: [], loading: false },
    proposal: { threadId: '', messages: [], loading: false },
  });
  const [inputMessage, setInputMessage] = useState('');
  const [isMinimized, setIsMinimized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threads, activeAgent]);

  const initializeAgent = async (agent: AgentType) => {
    const currentThread = threads[agent];
    if (currentThread.threadId || currentThread.loading) return;

    setThreads(prev => ({
      ...prev,
      [agent]: { ...prev[agent], loading: true }
    }));

    try {
      let initialMessage = '';
      let imagePath: string | undefined;

      if (agent === 'sustainability') {
        initialMessage = panoramaPath 
          ? `Analyze this location and provide sustainable redesign suggestions. Location: ${locationData?.address || 'Unknown'}`
          : 'Generate initial redesign ideas for sustainable urban development.';
        imagePath = panoramaPath || undefined;
      } else if (agent === 'indigenous') {
        initialMessage = locationData?.territory
          ? `This location is in ${locationData.territory}. What are the key indigenous perspectives to consider for development here?`
          : 'What are the key indigenous perspectives to consider for land development?';
      } else if (agent === 'proposal') {
        initialMessage = `What are the steps in the proposal workflow for a project at ${locationData?.address || 'this location'}?`;
      }

      const response = await createAgentChat(agent, initialMessage, imagePath);

      setThreads(prev => ({
        ...prev,
        [agent]: {
          threadId: response.thread_id,
          messages: [
            { role: 'user', content: response.user_message },
            { role: 'assistant', content: response.assistant_response }
          ],
          loading: false
        }
      }));
    } catch (error) {
      console.error(`Failed to initialize ${agent} agent:`, error);
      setThreads(prev => ({
        ...prev,
        [agent]: {
          ...prev[agent],
          loading: false,
          messages: [
            { role: 'assistant', content: `Failed to initialize agent. Error: ${error instanceof Error ? error.message : 'Unknown error'}` }
          ]
        }
      }));
    }
  };

  useEffect(() => {
    if (isOpen && !threads[activeAgent].threadId && !threads[activeAgent].loading) {
      initializeAgent(activeAgent);
    }
  }, [isOpen, activeAgent]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const currentThread = threads[activeAgent];
    if (!currentThread.threadId) {
      await initializeAgent(activeAgent);
      return;
    }

    const userMessage = inputMessage.trim();
    setInputMessage('');

    setThreads(prev => ({
      ...prev,
      [activeAgent]: {
        ...prev[activeAgent],
        messages: [...prev[activeAgent].messages, { role: 'user', content: userMessage }],
        loading: true
      }
    }));

    try {
      const response = await sendAgentMessage(currentThread.threadId, userMessage);

      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [
            ...prev[activeAgent].messages,
            { role: 'assistant', content: response.assistant_response }
          ],
          loading: false
        }
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [
            ...prev[activeAgent].messages,
            { role: 'assistant', content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}` }
          ],
          loading: false
        }
      }));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) return null;

  const agentNames = {
    sustainability: 'Sustainability',
    indigenous: 'Indigenous Context',
    proposal: 'Proposal Workflow'
  };

  const currentThread = threads[activeAgent];

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div 
        className={`bg-gray-900 border border-gray-700 rounded-lg shadow-2xl transition-all duration-300 ${
          isMinimized ? 'w-96 h-16' : 'w-[90vw] max-w-4xl h-[80vh]'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-bold text-white">AI Agents</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="text-gray-400 hover:text-white text-xl px-2"
            >
              {isMinimized ? '□' : '_'}
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-xl px-2"
            >
              ×
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Tabs */}
            <div className="flex border-b border-gray-700">
              {(Object.keys(agentNames) as AgentType[]).map((agent) => (
                <button
                  key={agent}
                  onClick={() => setActiveAgent(agent)}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeAgent === agent
                      ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  {agentNames[agent]}
                </button>
              ))}
            </div>

            {/* Chat Area */}
            <div className="flex flex-col h-[calc(80vh-8rem)]">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {currentThread.messages.length === 0 && !currentThread.loading && (
                  <div className="text-center text-gray-500 py-8">
                    Starting conversation with {agentNames[activeAgent]} Agent...
                  </div>
                )}

                {currentThread.messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-100'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1 opacity-75">
                        {message.role === 'user' ? 'You' : agentNames[activeAgent]}
                      </div>
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                    </div>
                  </div>
                ))}

                {currentThread.loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-800 text-gray-100 rounded-lg px-4 py-2">
                      <div className="text-xs font-semibold mb-1 opacity-75">
                        {agentNames[activeAgent]}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <div className="animate-pulse">Thinking...</div>
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-700 p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={`Message ${agentNames[activeAgent]} Agent...`}
                    disabled={currentThread.loading}
                    className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || currentThread.loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
