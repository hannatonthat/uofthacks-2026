'use client';

import { useEffect, useRef, useState } from 'react';
import { createAgentChat, sendAgentMessage, ChatMessage, deleteThread } from '@/lib/api';
import { 
  trackAgentResponseRated,
  getDeviceId,
  LocationData
} from '@/lib/amplitude';

interface PanoramaViewerProps {
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
  imageHistory: string[];
  currentImageIndex: number;
}

interface MessageRating {
  messageIndex: number;
  rating: 1 | -1;
}

// Declare pannellum on window for TypeScript
declare global {
  interface Window {
    pannellum: any;
  }
}

export default function PanoramaViewer({ isOpen, onClose, panoramaPath, locationData }: PanoramaViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const pannellumViewerRef = useRef<any>(null);
  const scriptLoadedRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Agent state
  const [sidebarWidth, setSidebarWidth] = useState(30); // percentage
  const [isDragging, setIsDragging] = useState(false);
  const [activeAgent, setActiveAgent] = useState<AgentType>('sustainability');
  const [threads, setThreads] = useState<Record<AgentType, AgentThread>>({
    sustainability: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
    indigenous: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
    proposal: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
  });
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Current display image (shared across all agents)
  const [currentDisplayImage, setCurrentDisplayImage] = useState<string | null>(null);
  
  // Rating state per agent
  const [ratings, setRatings] = useState<Record<AgentType, MessageRating[]>>({
    sustainability: [],
    indigenous: [],
    proposal: [],
  });

  // Get current thread
  const currentThread = threads[activeAgent];

  // Handle close and cleanup
  const handleClose = async () => {
    // Delete all threads
    for (const agentType of Object.keys(threads) as AgentType[]) {
      const thread = threads[agentType];
      if (thread.threadId) {
        try {
          await deleteThread(thread.threadId);
          console.log(`Thread deleted for ${agentType}`);
        } catch (error) {
          console.error(`Failed to delete ${agentType} thread:`, error);
        }
      }
    }
    
    // Reset state
    setThreads({
      sustainability: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
      indigenous: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
      proposal: { threadId: '', messages: [], imageHistory: [], currentImageIndex: 0 },
    });
    setInputMessage('');
    setCurrentDisplayImage(null);
    setRatings({
      sustainability: [],
      indigenous: [],
      proposal: [],
    });
    
    // Call the parent close handler
    onClose();
  };

  // Initialize image history when panorama loads
  useEffect(() => {
    if (isOpen && panoramaPath) {
      setCurrentDisplayImage(panoramaPath);
      // Initialize image history for all threads
      setThreads(prev => ({
        sustainability: { ...prev.sustainability, imageHistory: [panoramaPath], currentImageIndex: 0 },
        indigenous: { ...prev.indigenous, imageHistory: [panoramaPath], currentImageIndex: 0 },
        proposal: { ...prev.proposal, imageHistory: [panoramaPath], currentImageIndex: 0 },
      }));
    }
  }, [isOpen, panoramaPath]);

  // Initialize Agent when switching or opening
  useEffect(() => {
    if (isOpen && !currentThread.threadId && panoramaPath) {
      const initAgent = async () => {
        try {
          setLoading(true);
          
          // Different initial messages based on agent type
          let initialMessage = '';
          if (activeAgent === 'sustainability') {
            initialMessage = `Analyze this street view panorama and suggest sustainable improvements. Location: ${locationData?.address || 'Unknown'}`;
          } else if (activeAgent === 'indigenous') {
            initialMessage = `Analyze this street view panorama from an Indigenous perspective. Consider the land's traditional significance and Indigenous context. Location: ${locationData?.address || 'Unknown'}${locationData?.territory ? `, Territory: ${locationData.territory}` : ''}`;
          } else if (activeAgent === 'proposal') {
            initialMessage = `Analyze this street view panorama and create a comprehensive development proposal. Location: ${locationData?.address || 'Unknown'}`;
          }
          
          // Create agent chat with the panorama image path
          const response = await createAgentChat(activeAgent, initialMessage, panoramaPath);
          
          // Update the specific thread
          setThreads(prev => ({
            ...prev,
            [activeAgent]: {
              ...prev[activeAgent],
              threadId: response.thread_id,
              messages: [
                { role: 'user', content: response.user_message },
                { role: 'assistant', content: response.assistant_response }
              ],
            }
          }));
          
          // Debug: Log the response
          console.log(`Create ${activeAgent} Chat Response:`, {
            original: response.original_image_path,
            vision: response.vision_path,
            threadId: response.thread_id
          });
          
          // Update image history if vision exists
          if (response.vision_path) {
            setThreads(prev => ({
              ...prev,
              [activeAgent]: {
                ...prev[activeAgent],
                imageHistory: [panoramaPath, response.vision_path!],
                currentImageIndex: 1,
              }
            }));
            setCurrentDisplayImage(response.vision_path);
          }
        } catch (error) {
          console.error('Failed to initialize agent:', error);
          setThreads(prev => ({
            ...prev,
            [activeAgent]: {
              ...prev[activeAgent],
              messages: [
                { role: 'assistant', content: `Failed to initialize agent. Error: ${error instanceof Error ? error.message : 'Unknown error'}` }
              ],
            }
          }));
        } finally {
          setLoading(false);
        }
      };

      initAgent();
    }
  }, [isOpen, panoramaPath, activeAgent, currentThread.threadId, locationData]);

  // Pannellum viewer initialization
  useEffect(() => {
    if (!isOpen || !currentDisplayImage || !viewerRef.current) return;

    const initViewer = () => {
      try {
        // Clean up existing viewer if any
        if (pannellumViewerRef.current) {
          try {
            pannellumViewerRef.current.destroy();
          } catch (e) {
            // Ignore errors during cleanup
          }
        }

        // Check if pannellum is available on window
        if (typeof window !== 'undefined' && window.pannellum) {
          // Construct proper URL from file path
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
          const panoramaUrl = `${API_BASE_URL}/${currentDisplayImage}`;
          
          // Initialize Pannellum viewer
          pannellumViewerRef.current = window.pannellum.viewer(viewerRef.current, {
            type: 'equirectangular',
            panorama: panoramaUrl,
            autoLoad: true,
            showControls: true,
            mouseZoom: true,
            draggable: true,
            disableKeyboardCtrl: false,
            hfov: 100,
            pitch: 0,
            yaw: 0,
            hotSpotDebug: false,
            compass: false,
            showFullscreenCtrl: true,
            showZoomCtrl: true,
          });
        }
      } catch (error) {
        console.error('Failed to initialize Pannellum:', error);
      }
    };

    // Load Pannellum library via CDN if not already loaded
    if (!scriptLoadedRef.current && typeof window !== 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/pannellum.js';
      script.async = true;
      script.onload = () => {
        scriptLoadedRef.current = true;
        
        // Also load CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/pannellum.css';
        document.head.appendChild(link);
        
        // Initialize viewer after script loads
        initViewer();
      };
      document.body.appendChild(script);
    } else if (scriptLoadedRef.current) {
      // Script already loaded, just init viewer
      initViewer();
    }

    // Cleanup on unmount or when modal closes
    return () => {
      if (pannellumViewerRef.current) {
        try {
          pannellumViewerRef.current.destroy();
          pannellumViewerRef.current = null;
        } catch (error) {
          console.error('Error destroying Pannellum viewer:', error);
        }
      }
    };
  }, [isOpen, currentDisplayImage]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentThread.messages]);

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Handle sidebar resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      
      const newWidth = ((window.innerWidth - e.clientX) / window.innerWidth) * 100;
      // Constrain between 25% and 50%
      setSidebarWidth(Math.min(Math.max(newWidth, 25), 50));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !currentThread.threadId || loading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Add user message to current thread
    setThreads(prev => ({
      ...prev,
      [activeAgent]: {
        ...prev[activeAgent],
        messages: [...prev[activeAgent].messages, { role: 'user', content: userMessage }]
      }
    }));
    setLoading(true);

    try {
      // Send message to agent
      const response = await sendAgentMessage(currentThread.threadId, userMessage);
      
      // Add assistant response to current thread
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [...prev[activeAgent].messages, { role: 'assistant', content: response.assistant_response }]
        }
      }));
      
      // Debug: Log the response
      console.log(`Add ${activeAgent} Message Response:`, {
        original: response.original_image_path,
        vision: response.vision_path,
        currentHistory: currentThread.imageHistory
      });
      
      // Add new vision to history if generated
      if (response.vision_path) {
        console.log('Adding new vision to history:', response.vision_path);
        const newHistory = [...currentThread.imageHistory, response.vision_path];
        const newIndex = newHistory.length - 1;
        setThreads(prev => ({
          ...prev,
          [activeAgent]: {
            ...prev[activeAgent],
            imageHistory: newHistory,
            currentImageIndex: newIndex,
          }
        }));
        setCurrentDisplayImage(response.vision_path);
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [
            ...prev[activeAgent].messages,
            { role: 'assistant', content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}` }
          ]
        }
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleImageNavigation = (direction: 'prev' | 'next') => {
    const currentIndex = currentThread.currentImageIndex;
    const history = currentThread.imageHistory;
    
    if (direction === 'prev' && currentIndex > 0) {
      const newIndex = currentIndex - 1;
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          currentImageIndex: newIndex,
        }
      }));
      setCurrentDisplayImage(history[newIndex]);
    } else if (direction === 'next' && currentIndex < history.length - 1) {
      const newIndex = currentIndex + 1;
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          currentImageIndex: newIndex,
        }
      }));
      setCurrentDisplayImage(history[newIndex]);
    }
  };

  const handleRating = async (messageIndex: number, rating: 1 | -1) => {
    if (!currentThread.threadId) return;

    // Find the user message and agent response
    const userMessage = currentThread.messages[messageIndex - 1]?.content || '';
    const agentResponse = currentThread.messages[messageIndex]?.content || '';

    // Update local state for current agent
    setRatings(prev => ({
      ...prev,
      [activeAgent]: [
        ...prev[activeAgent].filter(r => r.messageIndex !== messageIndex),
        { messageIndex, rating }
      ]
    }));

    // Track with Amplitude
    const location: LocationData | undefined = locationData ? {
      lat: locationData.lat,
      lon: locationData.lon,
      territory: locationData.territory,
      address: locationData.address,
    } : undefined;

    trackAgentResponseRated(
      activeAgent,
      currentThread.threadId,
      messageIndex,
      rating,
      userMessage,
      agentResponse,
      location
    );

    // Send to backend for storage and AI analysis
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/api/ratings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: getDeviceId(),
          thread_id: currentThread.threadId,
          agent_type: activeAgent,
          message_index: messageIndex,
          rating,
          context: {
            user_message: userMessage,
            agent_response: agentResponse,
            location: locationData ? {
              lat: locationData.lat,
              lon: locationData.lon,
            } : undefined,
          }
        }),
      });
    } catch (error) {
      console.error('Failed to save rating:', error);
    }
  };

  const getRatingForMessage = (messageIndex: number): 1 | -1 | null => {
    const rating = ratings[activeAgent].find(r => r.messageIndex === messageIndex);
    return rating ? rating.rating : null;
  };

  const getAgentDisplayName = (agent: AgentType): string => {
    switch (agent) {
      case 'sustainability':
        return 'Sustainability Agent';
      case 'indigenous':
        return 'Indigenous Agent';
      case 'proposal':
        return 'Workflow Agent';
    }
  };

  const getInputPlaceholder = (agent: AgentType): string => {
    switch (agent) {
      case 'sustainability':
        return 'Ask for sustainable improvements...';
      case 'indigenous':
        return 'Ask about Indigenous context...';
      case 'proposal':
        return 'Ask about workflow and proposals...';
    }
  };

  if (!isOpen || !panoramaPath) return null;

  return (
    <div className="fixed inset-0 z-[3000] bg-black">
      {/* Custom Scrollbar Styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #000000;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #292524;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #44403c;
        }
      `}</style>
      {/* Close Button */}
      <button
        onClick={handleClose}
        className="absolute top-4 right-4 z-[3001] text-stone-300 hover:text-white text-xl cursor-pointer"
        aria-label="Close panorama viewer"
      >
        ×
      </button>

      {/* Main Content Area */}
      <div className="flex h-full relative">
        {/* Panorama Viewer - Dynamic width */}
        <div className="relative bg-black" style={{ width: `${100 - sidebarWidth}%` }}>
          {/* Panorama viewer container */}
          <div 
            ref={viewerRef}
            className="w-full h-full"
            style={{ 
              width: '100%', 
              height: '100%',
              position: 'relative'
            }}
          />

          {/* Image History Navigation */}
          {currentThread.imageHistory.length > 1 && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 backdrop-blur-sm text-white px-4 py-2 rounded-lg flex items-center gap-4 border border-stone-800">
              <button
                onClick={() => handleImageNavigation('prev')}
                disabled={currentThread.currentImageIndex === 0}
                className="disabled:opacity-30 disabled:cursor-not-allowed hover:text-stone-300 transition-colors text-sm"
              >
                ← Previous
              </button>
              <span className="text-xs text-stone-300">
                {currentThread.currentImageIndex === 0 ? 'Original' : `Vision ${currentThread.currentImageIndex}`}
                {' '}({currentThread.currentImageIndex + 1}/{currentThread.imageHistory.length})
              </span>
              <button
                onClick={() => handleImageNavigation('next')}
                disabled={currentThread.currentImageIndex === currentThread.imageHistory.length - 1}
                className="disabled:opacity-30 disabled:cursor-not-allowed hover:text-stone-300 transition-colors text-sm"
              >
                Next →
              </button>
            </div>
          )}
        </div>

        {/* Draggable Divider */}
        <div
          className="w-1 bg-neutral-900 hover:bg-neutral-700 cursor-col-resize relative group transition-colors"
          onMouseDown={() => setIsDragging(true)}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* Agent Sidebar - Dynamic width */}
        <div className="bg-black flex flex-col relative" style={{ width: `${sidebarWidth}%` }}>
          <>
              {/* Sidebar Header with Tabs */}
              <div className="border-b border-stone-800">
                <div className="flex items-center justify-between p-4 pb-3">
                  <h3 className="text-white font-semibold text-sm">AI Agents</h3>
                </div>
                
                {/* Agent Tabs */}
                <div className="flex gap-1 px-4 pb-2">
                  <button
                    onClick={() => setActiveAgent('sustainability')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer ${
                      activeAgent === 'sustainability'
                        ? 'bg-stone-800 text-white'
                        : 'text-stone-400 hover:text-white hover:bg-stone-900'
                    }`}
                  >
                    Sustainability
                  </button>
                  <button
                    onClick={() => setActiveAgent('indigenous')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer ${
                      activeAgent === 'indigenous'
                        ? 'bg-stone-800 text-white'
                        : 'text-stone-400 hover:text-white hover:bg-stone-900'
                    }`}
                  >
                    Indigenous
                  </button>
                  <button
                    onClick={() => setActiveAgent('proposal')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors cursor-pointer ${
                      activeAgent === 'proposal'
                        ? 'bg-stone-800 text-white'
                        : 'text-stone-400 hover:text-white hover:bg-stone-900'
                    }`}
                  >
                    Workflow
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
                {currentThread.messages.map((message, index) => (
                  <div key={index}>
                    <div
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg px-3 py-2 ${
                          message.role === 'user'
                            ? 'bg-stone-800 text-white'
                            : 'bg-stone-900 text-stone-100 border border-stone-800'
                        }`}
                      >
                        <div className="text-xs font-medium mb-1 text-stone-400">
                          {message.role === 'user' ? 'You' : getAgentDisplayName(activeAgent)}
                        </div>
                        <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                      </div>
                    </div>
                    
                    {/* Rating buttons for assistant messages */}
                    {message.role === 'assistant' && index > 0 && (
                      <div className="flex justify-start mt-1 ml-2">
                        <div className="flex gap-1.5 text-xs">
                          <button
                            onClick={() => handleRating(index, 1)}
                            className={`px-2 py-1 rounded transition-colors ${
                              getRatingForMessage(index) === 1
                                ? 'bg-stone-700 text-white'
                                : 'bg-stone-900 text-stone-500 hover:bg-stone-800 hover:text-stone-300'
                            }`}
                            title="Helpful response"
                          >
                            👍
                          </button>
                          <button
                            onClick={() => handleRating(index, -1)}
                            className={`px-2 py-1 rounded transition-colors ${
                              getRatingForMessage(index) === -1
                                ? 'bg-stone-700 text-white'
                                : 'bg-stone-900 text-stone-500 hover:bg-stone-800 hover:text-stone-300'
                            }`}
                            title="Not helpful"
                          >
                            👎
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-stone-900 text-stone-100 rounded-lg px-3 py-2 border border-stone-800">
                      <div className="text-xs font-medium mb-1 text-stone-400">
                        {getAgentDisplayName(activeAgent)}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <div className="animate-pulse">Analyzing...</div>
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 bg-stone-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-1.5 h-1.5 bg-stone-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-1.5 h-1.5 bg-stone-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-stone-800 p-3">
                <div className="relative">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={getInputPlaceholder(activeAgent)}
                    disabled={loading}
                    className="w-full bg-stone-900 text-white px-3 py-2 pr-10 rounded-lg border border-stone-800 focus:outline-none focus:border-stone-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm placeholder-stone-500"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || loading}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-white hover:text-stone-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-lg"
                  >
                    →
                  </button>
                </div>
              </div>
            </>
        </div>
      </div>
    </div>
  );
}
