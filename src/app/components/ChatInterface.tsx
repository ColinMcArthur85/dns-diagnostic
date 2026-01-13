"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, Loader, MessageCircle, X } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatInterfaceProps {
  diagnosticData: any;
  audience: 'customer' | 'support';
  onClose: () => void;
}

export default function ChatInterface({ diagnosticData, audience, onClose }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Start conversation when component mounts
    startConversation();
  }, []);

  const startConversation = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'start',
          diagnostic_data: diagnosticData,
          audience
        })
      });

      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('Chat endpoint not found. Ensure you are using "vercel dev".');
        }
        const text = await res.text();
        try {
          const errorJson = JSON.parse(text);
          throw new Error(errorJson.error || `Server error: ${res.status}`);
        } catch {
          throw new Error(`Server error ${res.status}`);
        }
      }

      const data = await res.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      setSessionId(data.session_id);
      setSuggestedQuestions(data.suggested_questions || []);
      setMessages([
        { role: 'assistant', content: data.opening_message }
      ]);
    } catch (error: any) {
      setMessages([
        { role: 'assistant', content: `Sorry, I couldn't start the conversation: ${error.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || !sessionId) return;

    const userMessage: Message = { role: 'user', content: textToSend };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'chat',
          session_id: sessionId,
          message: textToSend,
          history: messages,
          diagnostic_data: diagnosticData,
          audience
        })
      });

      if (!res.ok) {
        const text = await res.text();
        try {
          const errorJson = JSON.parse(text);
          throw new Error(errorJson.error || `Server error: ${res.status}`);
        } catch {
          throw new Error(`Server error ${res.status}`);
        }
      }

      const data = await res.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      const assistantMessage: Message = { role: 'assistant', content: data.message };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: Message = { 
        role: 'assistant', 
        content: `Sorry, I encountered an error: ${error.message}` 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-[#0d0d0d] border border-[#262626] rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50">
      {/* Header */}
      <div className="p-4 bg-linear-to-r from-purple-900/20 to-blue-900/20 border-b border-[#262626] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-600/20 flex items-center justify-center">
            <MessageCircle size={20} className="text-purple-400" />
          </div>
          <div>
            <div className="font-bold text-white text-sm">DNS Assistant</div>
            <div className="text-xs text-gray-400 flex items-center gap-2">
              {audience === 'customer' ? 'Customer Mode' : 'Support Mode'}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          title="Close chat"
        >
          <X size={18} className="text-gray-400" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-purple-600/20 flex items-center justify-center shrink-0">
                  <Bot size={16} className="text-purple-400" />
                </div>
              )}
              
              <div className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-600/20 text-blue-100 border border-blue-500/30'
                  : 'bg-[#161616] text-gray-300 border border-[#262626]'
              }`}>
                <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center shrink-0">
                  <User size={16} className="text-blue-400" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-purple-600/20 flex items-center justify-center">
              <Loader size={16} className="text-purple-400 animate-spin" />
            </div>
            <div className="bg-[#161616] border border-[#262626] rounded-2xl px-4 py-2">
              <div className="text-sm text-gray-400">Thinking...</div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      {suggestedQuestions.length > 0 && messages.length === 1 && (
        <div className="px-4 pb-2">
          <div className="text-xs text-gray-500 mb-2">Suggested questions:</div>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.slice(0, 3).map((question, idx) => (
              <button
                key={idx}
                onClick={() => sendMessage(question)}
                className="text-xs bg-[#161616] border border-[#262626] hover:border-purple-500/50 rounded-lg px-3 py-1.5 text-gray-400 hover:text-purple-400 transition-all"
                disabled={loading}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-[#262626]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
            placeholder="Ask a question..."
            className="flex-1 bg-[#161616] border border-[#262626] rounded-lg px-4 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="shrink-0 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg p-2 transition-colors"
            title="Send message"
          >
            <Send size={18} className="text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
