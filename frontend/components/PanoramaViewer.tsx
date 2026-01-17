'use client';

import { useEffect, useRef, useState } from 'react';
import { createSustainabilityChat, addSustainabilityMessage, ChatMessage, deleteThread } from '@/lib/api';

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
  const [agentOpen, setAgentOpen] = useState(true);
  const [threadId, setThreadId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Image history state
  const [imageHistory, setImageHistory] = useState<string[]>([]);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [currentDisplayImage, setCurrentDisplayImage] = useState<string | null>(null);

  // Handle close and cleanup
  const handleClose = async () => {
    // Delete the thread and chat history
    if (threadId) {
      try {
        await deleteThread(threadId);
        console.log('Thread deleted successfully');
      } catch (error) {
        console.error('Failed to delete thread:', error);
      }
    }
    
    // Reset state
    setThreadId('');
    setMessages([]);
    setInputMessage('');
    setImageHistory([]);
    setCurrentImageIndex(0);
    setCurrentDisplayImage(null);
    
    // Call the parent close handler
    onClose();
  };

  // Initialize image history when panorama loads
  useEffect(() => {
    if (isOpen && panoramaPath) {
      setImageHistory([panoramaPath]);
      setCurrentImageIndex(0);
      setCurrentDisplayImage(panoramaPath);
    }
  }, [isOpen, panoramaPath]);

  // Initialize Sustainability Agent when modal opens
  useEffect(() => {
    if (isOpen && !threadId && panoramaPath) {
      const initAgent = async () => {
        try {
          setLoading(true);
          const initialMessage = `Analyze this street view panorama and suggest sustainable improvements. Location: ${locationData?.address || 'Unknown'}`;
          
          // Create sustainability agent with the panorama image path
          const response = await createSustainabilityChat(initialMessage, panoramaPath);
          
          setThreadId(response.thread_id);
          setMessages([
            { role: 'user', content: response.user_message },
            { role: 'assistant', content: response.assistant_response }
          ]);
          
          // Debug: Log the response
          console.log('Create Sustainability Chat Response:', {
            original: response.original_image_path,
            vision: response.vision_path,
            threadId: response.thread_id
          });
          
          // Initialize image history with both original and vision (if exists)
          const initialHistory = [panoramaPath]; // Start with original panorama
          if (response.vision_path) {
            initialHistory.push(response.vision_path);
            setCurrentImageIndex(1); // Show the vision
            setCurrentDisplayImage(response.vision_path);
          }
          setImageHistory(initialHistory);
        } catch (error) {
          console.error('Failed to initialize agent:', error);
          setMessages([
            { role: 'assistant', content: `Failed to initialize agent. Error: ${error instanceof Error ? error.message : 'Unknown error'}` }
          ]);
        } finally {
          setLoading(false);
        }
      };

      initAgent();
    }
  }, [isOpen, panoramaPath, threadId, locationData]);

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
  }, [messages]);

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

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !threadId || loading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      // Use add-sustainability-chat for follow-up messages with vision generation
      const response = await addSustainabilityMessage(threadId, userMessage);
      
      setMessages(prev => [...prev, { role: 'assistant', content: response.assistant_response }]);
      
      // Debug: Log the response
      console.log('Add Sustainability Message Response:', {
        original: response.original_image_path,
        vision: response.vision_path,
        currentHistory: imageHistory
      });
      
      // Add new vision to history if generated
      if (response.vision_path) {
        console.log('Adding new vision to history:', response.vision_path);
        setImageHistory(prev => [...prev, response.vision_path!]);
        const newIndex = imageHistory.length; // This will be the index of the newly added vision
        setCurrentImageIndex(newIndex);
        setCurrentDisplayImage(response.vision_path);
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}` }
      ]);
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
    if (direction === 'prev' && currentImageIndex > 0) {
      const newIndex = currentImageIndex - 1;
      setCurrentImageIndex(newIndex);
      setCurrentDisplayImage(imageHistory[newIndex]);
    } else if (direction === 'next' && currentImageIndex < imageHistory.length - 1) {
      const newIndex = currentImageIndex + 1;
      setCurrentImageIndex(newIndex);
      setCurrentDisplayImage(imageHistory[newIndex]);
    }
  };

  if (!isOpen || !panoramaPath) return null;

  return (
    <div className="fixed inset-0 z-[3000] bg-black">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-[3001] bg-black/90 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-white font-bold text-lg">360° Panorama Viewer</h2>
          <p className="text-gray-400 text-sm">Drag to look around • Scroll to zoom</p>
        </div>
        <button
          onClick={handleClose}
          className="text-white hover:text-gray-300 text-2xl w-8 h-8 flex items-center justify-center"
          aria-label="Close panorama viewer"
        >
          ×
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex h-full pt-16">
        {/* Panorama Viewer - 70% width */}
        <div className="relative flex-1 bg-black">
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
          {imageHistory.length > 1 && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/80 text-white px-4 py-2 rounded-lg flex items-center gap-4">
              <button
                onClick={() => handleImageNavigation('prev')}
                disabled={currentImageIndex === 0}
                className="disabled:opacity-30 disabled:cursor-not-allowed hover:text-blue-400 transition-colors"
              >
                ← Previous
              </button>
              <span className="text-sm">
                {currentImageIndex === 0 ? 'Original' : `Vision ${currentImageIndex}`}
                {' '}({currentImageIndex + 1}/{imageHistory.length})
              </span>
              <button
                onClick={() => handleImageNavigation('next')}
                disabled={currentImageIndex === imageHistory.length - 1}
                className="disabled:opacity-30 disabled:cursor-not-allowed hover:text-blue-400 transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </div>

        {/* Agent Sidebar - 30% width */}
        <div className={`${agentOpen ? 'w-[30%]' : 'w-0'} bg-gray-900 border-l border-gray-700 transition-all duration-300 overflow-hidden flex flex-col`}>
          {agentOpen && (
            <>
              {/* Sidebar Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-700">
                <h3 className="text-white font-bold">Sustainability Agent</h3>
                <button
                  onClick={() => setAgentOpen(false)}
                  className="text-gray-400 hover:text-white text-xl"
                >
                  →
                </button>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-4 py-2 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-100'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1 opacity-75">
                        {message.role === 'user' ? 'You' : 'Sustainability Agent'}
                      </div>
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-800 text-gray-100 rounded-lg px-4 py-2">
                      <div className="text-xs font-semibold mb-1 opacity-75">
                        Sustainability Agent
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <div className="animate-pulse">Analyzing and generating vision...</div>
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
                    placeholder="Ask for sustainable improvements..."
                    disabled={loading}
                    className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                  >
                    Send
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Toggle Agent Sidebar Button (when closed) */}
        {!agentOpen && (
          <button
            onClick={() => setAgentOpen(true)}
            className="absolute right-0 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-2 py-4 rounded-l-lg shadow-lg transition-colors"
          >
            ← AI
          </button>
        )}
      </div>
    </div>
  );
}
