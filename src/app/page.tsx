"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Shield, Info, ArrowRight, CheckCircle, AlertTriangle, Terminal, Globe, Mail, Copy, Check, MessageCircle } from 'lucide-react';
import ChatInterface from './components/ChatInterface';

export default function Home() {
  const [domain, setDomain] = useState('');
  const [platform, setPlatform] = useState('attractwell');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [selectedSections, setSelectedSections] = useState<string[]>(['all']);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiAudience, setAiAudience] = useState<'customer' | 'support' | 'both'>('customer');
  const [activeAiTab, setActiveAiTab] = useState<'customer' | 'support'>('customer');
  const [showChat, setShowChat] = useState(false);  // Phase 3: Chat interface
  
  // Intent questions
  const [intent, setIntent] = useState({
    has_external_dependencies: false,
    email_managed_by_platform: false,
    comfortable_editing_dns: true,
    registrar_known: true,
    delegate_dns_management: false,
  });

  const availableSections = [
    { id: 'all', label: 'All Records', icon: <Globe size={14} /> },
    { id: 'web', label: 'Web Hosting', icon: <Shield size={14} /> },
    { id: 'email', label: 'Email Service', icon: <Mail size={14} /> },
    { id: 'A', label: 'A Record' },
    { id: 'CNAME', label: 'CNAME' },
    { id: 'MX', label: 'MX' },
    { id: 'TXT', label: 'TXT' },
    { id: 'SPF', label: 'SPF' },
    { id: 'DMARC', label: 'DMARC' },
    { id: 'DKIM', label: 'DKIM' },
    { id: 'NS', label: 'NS' },
  ];

  const toggleSection = (id: string) => {
    if (id === 'all') {
      setSelectedSections(['all']);
      return;
    }
    
    setSelectedSections(prev => {
      const next = prev.filter(s => s !== 'all');
      if (next.includes(id)) {
        const filtered = next.filter(s => s !== id);
        return filtered.length === 0 ? ['all'] : filtered;
      }
      return [...next, id];
    });
  };

  const handleDiagnose = async () => {
    if (!domain) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          domain, 
          platform, 
          sections: selectedSections,
          intent,
          ai_audience: aiAudience  // Phase 2: Send audience parameter
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="main-layout">
      {/* Hero Section */}
      <div className="max-w-4xl mx-auto text-center mb-16">
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="heading-primary"
        >
          DNS Diagnostics Pro
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-muted"
        >
          Analyze domain DNS records for GetOiling and AttractWell.
        </motion.p>

        {/* Search Bar */}
        <div className="space-y-6">
          <motion.div 
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="search-container"
          >
            <div className="flex-1 flex items-center px-4">
              <Search className="text-gray-500 mr-3" size={20} />
              <input 
                type="text"
                placeholder="Enter domain (e.g. example.com)"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="input-field"
              />
            </div>
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="select-field"
            >
              <option value="attractwell">AttractWell</option>
              <option value="getoiling">GetOiling</option>
            </select>
            <button 
              onClick={handleDiagnose}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Analyzing...' : 'Diagnose'}
            </button>
          </motion.div>

          {/* Section Selection Filters */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto"
          >
            {availableSections.map((section) => (
              <button
                key={section.id}
                onClick={() => toggleSection(section.id)}
                className={`
                  inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-all
                  ${selectedSections.includes(section.id) 
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.15)]' 
                    : 'bg-[#161616] text-gray-500 border border-[#262626] hover:border-gray-700 hover:text-gray-400'}
                `}
              >
                {section.icon}
                {section.label}
              </button>
            ))}
          </motion.div>

          {/* Advanced Options Toggle */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-center"
          >
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-gray-500 hover:text-gray-300 transition-colors inline-flex items-center gap-2"
            >
              <Info size={14} />
              {showAdvanced ? 'Hide' : 'Show'} Advanced Options
            </button>
          </motion.div>

          {/* Advanced Options Panel */}
          <AnimatePresence>
            {showAdvanced && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="max-w-2xl mx-auto overflow-hidden"
              >
                <div className="p-6 bg-[#161616] border border-[#262626] rounded-2xl space-y-4">
                  <h3 className="text-sm font-bold text-gray-300 mb-4 flex items-center gap-2">
                    <Shield size={16} />
                    Connection Configuration
                  </h3>
                  
                  <div className="space-y-3">
                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={intent.has_external_dependencies}
                        onChange={(e) => setIntent({ ...intent, has_external_dependencies: e.target.checked })}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-[#0d0d0d] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 group-hover:text-white transition-colors">
                          Domain has external dependencies (email, services, subdomains)
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          Check this if you're using third-party services that rely on DNS records
                        </div>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={intent.email_managed_by_platform}
                        onChange={(e) => setIntent({ ...intent, email_managed_by_platform: e.target.checked })}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-[#0d0d0d] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 group-hover:text-white transition-colors">
                          Email is managed by our platform
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          Check this if email hosting is handled by AttractWell/GetOiling
                        </div>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={intent.comfortable_editing_dns}
                        onChange={(e) => setIntent({ ...intent, comfortable_editing_dns: e.target.checked })}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-[#0d0d0d] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 group-hover:text-white transition-colors">
                          Comfortable editing DNS records
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          Uncheck if you need help with DNS configuration
                        </div>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={intent.registrar_known}
                        onChange={(e) => setIntent({ ...intent, registrar_known: e.target.checked })}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-[#0d0d0d] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 group-hover:text-white transition-colors">
                          I know my domain registrar
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          Uncheck if you're unsure where your domain is registered
                        </div>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={intent.delegate_dns_management}
                        onChange={(e) => setIntent({ ...intent, delegate_dns_management: e.target.checked })}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-[#0d0d0d] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 group-hover:text-white transition-colors">
                          I want you to manage DNS for me
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          We can handle the DNS configuration on your behalf
                        </div>
                      </div>
                    </label>

                    {/* Phase 2: AI Audience Selector */}
                    <div className="pt-4 border-t border-[#262626]">
                      <label className="block">
                        <div className="flex items-center gap-2 mb-3">
                          <Terminal size={14} className="text-purple-400" />
                          <span className="text-sm font-bold text-gray-300">AI Explanation Mode (Phase 2)</span>
                          <span className="bg-purple-500/10 text-purple-400 text-[8px] font-bold px-1.5 py-0.5 rounded uppercase">
                            New
                          </span>
                        </div>
                        <select
                          value={aiAudience}
                          onChange={(e) => setAiAudience(e.target.value as 'customer' | 'support' | 'both')}
                          className="w-full px-3 py-2 bg-[#0d0d0d] border border-gray-600 rounded-lg text-gray-300 text-sm focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500"
                        >
                          <option value="customer">Customer-Friendly (Plain English)</option>
                          <option value="support">Support Staff (Technical Details)</option>
                          <option value="both">Both Views (Toggle Between Them)</option>
                        </select>
                        <div className="text-xs text-gray-500 mt-2">
                          Controls how AI explains the results. Customer view uses simple language, Support view includes technical details.
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {loading && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="max-w-4xl mx-auto flex flex-col items-center gap-4 py-20"
          >
            <div className="w-16 h-16 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
            <p className="text-blue-400 font-mono tracking-widest animate-pulse uppercase text-xs">Performing deep DNS inspection...</p>
          </motion.div>
        )}

        {error && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto p-4 bg-red-950/30 border border-red-900/50 rounded-xl text-red-400 flex items-center gap-3"
          >
            <AlertTriangle size={20} />
            <p>{error}</p>
          </motion.div>
        )}

        {result && (
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-6xl mx-auto space-y-8 pb-20"
          >
            {/* Top Grid: Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard icon={<Globe className="text-blue-400"/>} title="Domain" value={result.domain} />
              <StatCard 
                icon={<Shield className="text-purple-400"/>} 
                title="Registrar" 
                value={typeof result.dns_snapshot.WHOIS?.registrar === 'string' ? result.dns_snapshot.WHOIS.registrar : (Array.isArray(result.dns_snapshot.WHOIS?.registrar) ? result.dns_snapshot.WHOIS.registrar[0] : 'Unknown')} 
              />
              <StatCard icon={<Mail className="text-green-400"/>} title="Email Provider" value={result.email_state.display_name} />
              <StatCard 
                icon={<Terminal className="text-amber-400"/>} 
                title="Nameservers" 
                value={result.dns_snapshot.WHOIS?.name_servers ? (Array.isArray(result.dns_snapshot.WHOIS.name_servers) ? result.dns_snapshot.WHOIS.name_servers.join(', ') : result.dns_snapshot.WHOIS.name_servers) : 'Unknown'} 
              />
            </div>
            
            {/* Internal Registrar Notice */}
            {result.delegate_access?.is_internal && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 bg-purple-950/20 border border-purple-500/30 rounded-2xl flex items-start gap-4"
              >
                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                  <Globe size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-purple-400 mb-1">Platform-Managed Domain Detected</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">
                    This domain appears to be registered with <strong>NameBright</strong>, our domain partner. 
                    <strong> Confirm that the domain has been registered with us before proceeding.</strong> (AKA, ask Colin and/or Greg if you don't have access to NameBright). 
                  </p>
                </div>
              </motion.div>
            )}

            {/* Success State */}
            {result.is_completed && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-8 bg-green-950/20 border border-green-500/30 rounded-2xl flex flex-col items-center text-center gap-4"
              >
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center text-green-500">
                  <CheckCircle size={40} />
                </div>
                <h2 className="text-2xl font-bold text-green-400">{result.status_message}</h2>
                <p className="text-gray-400 max-w-md">All DNS records are correctly configured and pointing to our servers. No further action is required.</p>
              </motion.div>
            )}
            {/* DNS Analysis Comparison Table */}
            {result.comparison && result.comparison.length > 0 && (
              <div className="card overflow-hidden">
                <div className="card-header">
                  <h3 className="font-bold flex items-center gap-3 text-lg">
                    <Search className="text-blue-400" size={20} />
                    DNS Record Comparison
                  </h3>
                  <span className="text-gray-500 text-xs font-mono">{result.domain}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-[#1c1c1c] text-gray-400 text-[10px] font-bold uppercase tracking-widest border-b border-[#262626]">
                        <th className="px-6 py-4">Record Type</th>
                        <th className="px-6 py-4">Current Value</th>
                        <th className="px-6 py-4">Target Value</th>
                        <th className="px-6 py-4 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#262626]">
                      {result.comparison.map((item: any, idx: number) => (
                        <tr key={idx} className="hover:bg-white/2 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex flex-col gap-1">
                              <div className="text-sm font-semibold text-gray-200">{item.label}</div>
                              {item.is_required && (
                                <span className="w-fit text-[9px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Required</span>
                              )}
                              {item.is_recommended && (
                                <span className="w-fit text-[9px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Recommended</span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 max-w-md">
                            <div className="text-xs font-mono text-gray-400 wrap-break-word line-clamp-2 hover:line-clamp-none transition-all">
                              {item.current}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-xs font-mono text-blue-300 wrap-break-word">
                              {item.target}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <StatusBadge status={item.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Phase 2: AI Analysis Section with Support/Customer Toggle */}
            {(result.ai_insights?.summary || result.ai_insights?.support || result.ai_insights?.customer) && (
              <div className="card overflow-hidden">
                <div className="card-header">
                  <div className="flex items-center gap-3">
                    <Terminal className="text-blue-400" size={20} />
                    <h3 className="font-bold text-lg">AI Analysis</h3>
                    <span className="bg-purple-500/10 text-purple-400 text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                      Phase 2
                    </span>
                  </div>
                  
                  {/* Tabs for Support vs Customer view (if both are available) */}
                  {result.ai_insights?.support && result.ai_insights?.customer && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => setActiveAiTab('customer')}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                          activeAiTab === 'customer'
                            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/50'
                            : 'bg-[#161616] text-gray-500 border border-[#262626] hover:text-gray-300'
                        }`}
                      >
                        Customer View
                      </button>
                      <button
                        onClick={() => setActiveAiTab('support')}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                          activeAiTab === 'support'
                            ? 'bg-purple-600/20 text-purple-400 border border-purple-500/50'
                            : 'bg-[#161616] text-gray-500 border border-[#262626] hover:text-gray-300'
                        }`}
                      >
                        Support View
                      </button>
                    </div>
                  )}
                </div>
                
                <div className="card-body space-y-6">
                  {/* Show single-audience results (legacy format or single mode) */}
                  {result.ai_insights?.summary && !result.ai_insights?.support && (
                    <>
                      <div className="text-gray-300 leading-relaxed text-sm">
                        {result.ai_insights.summary}
                      </div>
                      {result.ai_insights.next_steps && Array.isArray(result.ai_insights.next_steps) && (
                        <div className="space-y-2">
                          <div className="text-xs uppercase tracking-wider text-gray-500 font-bold">Next Steps</div>
                          <div className="grid grid-cols-1 gap-2">
                            {result.ai_insights.next_steps.map((step: string, i: number) => (
                              <div key={i} className="flex items-start gap-3 p-3 bg-[#161616]/50 border border-[#262626] rounded-lg">
                                <div className="w-5 h-5 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold shrink-0">
                                  {i + 1}
                                </div>
                                <p className="text-gray-300 text-sm leading-relaxed">{step}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Customer View */}
                  {result.ai_insights?.customer && (activeAiTab === 'customer' || !result.ai_insights?.support) && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">Customer-Friendly Explanation</span>
                      </div>
                      
                      {result.ai_insights.customer.summary && (
                        <div className="text-gray-300 leading-relaxed">{result.ai_insights.customer.summary}</div>
                      )}
                      
                      {result.ai_insights.customer.what_this_means && (
                        <div className="p-4 bg-blue-950/20 border border-blue-500/20 rounded-lg">
                          <div className="text-xs text-blue-400 font-bold mb-2">What This Means</div>
                          <div className="text-gray-300 text-sm leading-relaxed">{result.ai_insights.customer.what_this_means}</div>
                        </div>
                      )}
                      
                      {result.ai_insights.customer.next_steps && Array.isArray(result.ai_insights.customer.next_steps) && result.ai_insights.customer.next_steps.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs uppercase tracking-wider text-gray-500 font-bold">Next Steps</div>
                          <div className="grid grid-cols-1 gap-2">
                            {result.ai_insights.customer.next_steps.map((step: string, i: number) => (
                              <div key={i} className="flex items-start gap-3 p-3 bg-[#161616]/50 border border-[#262626] rounded-lg">
                                <div className="w-5 h-5 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold shrink-0">
                                  {i + 1}
                                </div>
                                <p className="text-gray-300 text-sm leading-relaxed">{step}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Support View */}
                  {result.ai_insights?.support && activeAiTab === 'support' && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">Technical Summary for Support Staff</span>
                      </div>
                      
                      {result.ai_insights.support.technical_summary && (
                        <div className="p-4 bg-purple-950/20 border border-purple-500/20 rounded-lg">
                          <div className="text-purple-400 font-mono text-sm leading-relaxed">{result.ai_insights.support.technical_summary}</div>
                        </div>
                      )}
                      
                      {result.ai_insights.support.issues && Array.isArray(result.ai_insights.support.issues) && result.ai_insights.support.issues.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs uppercase tracking-wider text-gray-500 font-bold">Issues Detected</div>
                          <div className="space-y-2">
                            {result.ai_insights.support.issues.map((issue: string, i: number) => (
                              <div key={i} className="flex items-start gap-3 p-3 bg-red-950/20 border border-red-500/30 rounded-lg">
                                <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                                <p className="text-gray-300 text-sm leading-relaxed">{issue}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {result.ai_insights.support.actions_required && Array.isArray(result.ai_insights.support.actions_required) && result.ai_insights.support.actions_required.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs uppercase tracking-wider text-gray-500 font-bold">Actions Required</div>
                          <div className="grid grid-cols-1 gap-2">
                            {result.ai_insights.support.actions_required.map((action: string, i: number) => (
                              <div key={i} className="flex items-start gap-3 p-3 bg-[#161616]/50 border border-[#262626] rounded-lg">
                                <div className="w-5 h-5 rounded-full bg-green-600/20 text-green-400 flex items-center justify-center text-xs font-bold shrink-0">
                                  {i + 1}
                                </div>
                                <p className="text-gray-300 text-sm font-mono leading-relaxed">{action}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {result.ai_insights.support.notes && Array.isArray(result.ai_insights.support.notes) && result.ai_insights.support.notes.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs uppercase tracking-wider text-gray-500 font-bold">Support Notes</div>
                          <div className="space-y-1">
                            {result.ai_insights.support.notes.map((note: string, i: number) => (
                              <div key={i} className="flex items-start gap-2 text-sm text-gray-400">
                                <Info size={14} className="shrink-0 mt-0.5" />
                                <span>{note}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Guardrails indicator */}
                  {result.ai_insights?._metadata?.guardrails_active && (
                    <div className="text-[10px] text-gray-600 italic flex items-center gap-2 pt-2 border-t border-[#262626]">
                      <Shield size={12} />
                      Phase 2 Guardrails Active: AI is bounded to diagnostic data only
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Recommended Actions */}
            {result.recommended_actions.length > 0 && (
              <div className="card overflow-hidden shadow-xl">
                <div className="card-header">
                  <h3 className="font-bold flex items-center gap-3 text-lg">
                    <CheckCircle className="text-green-500" size={20} />
                    Action Plan
                  </h3>
                  <span className="bg-green-500/10 text-green-500 text-[10px] font-bold px-2 py-1 rounded uppercase">Priority: High</span>
                </div>
                <div className="card-body space-y-6">
                  {result.recommended_actions.map((action: any, idx: number) => (
                    <ActionItem key={idx} action={action} idx={idx} />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Phase 3: Floating Chat Button */}
      {result && !showChat && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.5 }}
          onClick={() => setShowChat(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-linear-to-br from-purple-600 to-blue-600 rounded-full shadow-2xl flex items-center justify-center hover:scale-110 transition-transform z-40 group"
          title="Ask questions about this diagnostic"
        >
          <MessageCircle size={24} className="text-white" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-[#0d0d0d] animate-pulse"></span>
          <div className="absolute top-0 right-0 -mr-2 -mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="bg-black/90 text-white text-xs px-3 py-1.5 rounded-lg whitespace-nowrap shadow-xl">
              Ask questions (Phase 3)
            </div>
          </div>
        </motion.button>
      )}

      {/* Phase 3: Chat Interface */}
      {showChat && result && (
        <ChatInterface
          diagnosticData={result}
          audience={aiAudience === 'both' ? activeAiTab : aiAudience}
          onClose={() => setShowChat(false)}
        />
      )}
    </main>
  );
}

function ActionItem({ action, idx }: { action: any, idx: number }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3">
      <div className="action-item">
        <div className="action-number">
          {idx + 1}
        </div>
        <div className="flex-1">
          {action.action === 'change_nameservers' ? (
            <>
              <div className="font-semibold text-gray-200 mb-2">Update Nameservers</div>
              <div className="font-mono text-sm text-gray-500">
                Set nameservers to: <span className="text-blue-300">{Array.isArray(action.values) ? action.values.join(', ') : action.values}</span>
              </div>
            </>
          ) : (
            <>
              <div className="font-semibold text-gray-200 mb-2">Add {action.type} Record</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">Type:</span> <span className="text-blue-300 font-mono">{action.type}</span>
                </div>
                <div>
                  <span className="text-gray-500">Host:</span> <span className="text-blue-300 font-mono">{action.host}</span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">Value:</span> <span className="text-purple-300 font-mono">{action.value}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Copy/Paste Block */}
      <div className="ml-11 relative group">
        <div className="bg-[#0d0d0d] border border-[#262626] rounded-lg p-4 hover:border-blue-500/30 transition-colors">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-1">
              <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-2">Ready to Copy</div>
              {action.action === 'change_nameservers' ? (
                <div className="space-y-1">
                  {(Array.isArray(action.values) ? action.values : [action.values]).map((ns: string, i: number) => (
                    <div key={i} className="font-mono text-sm text-blue-300">
                      {ns}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-1">
                  <div className="font-mono text-xs">
                    <span className="text-gray-500">Type:</span> <span className="text-blue-300">{action.type}</span>
                  </div>
                  <div className="font-mono text-xs">
                    <span className="text-gray-500">Name/Host:</span> <span className="text-blue-300">{action.host}</span>
                  </div>
                  <div className="font-mono text-xs">
                    <span className="text-gray-500">Value/Target:</span> <span className="text-purple-300">{action.value}</span>
                  </div>
                  {action.type === 'MX' && (
                    <div className="font-mono text-xs">
                      <span className="text-gray-500">Priority:</span> <span className="text-blue-300">10</span>
                    </div>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => {
                const copyText = action.action === 'change_nameservers' 
                  ? (Array.isArray(action.values) ? action.values.join('\n') : action.values)
                  : `Type: ${action.type}\nHost: ${action.host}\nValue: ${action.value}`;
                handleCopy(copyText);
              }}
              className="shrink-0 p-2 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 rounded-lg transition-all group-hover:border-blue-500/50"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check size={16} className="text-green-400" />
              ) : (
                <Copy size={16} className="text-blue-400" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, title, value }: { icon: React.ReactNode, title: string, value: string }) {
  return (
    <div className="stat-card">
      <div className="flex items-center gap-3 mb-3">
        <div className="stat-icon-wrapper">
          {icon}
        </div>
        <span className="stat-label">{title}</span>
      </div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: 'matched' | 'missing' | 'conflict' | 'external' | 'info' | 'different' }) {
  const configs = {
    matched: { icon: <CheckCircle size={14} />, text: 'Matched', class: 'bg-green-500/10 text-green-500' },
    missing: { icon: <AlertTriangle size={14} />, text: 'Missing', class: 'bg-red-500/10 text-red-500' },
    conflict: { icon: <AlertTriangle size={14} />, text: 'Conflict', class: 'bg-red-500/10 text-red-400' },
    different: { icon: <Info size={14} />, text: 'Different', class: 'bg-blue-500/10 text-blue-400' },
    external: { icon: <Globe size={14} />, text: 'External', class: 'bg-blue-500/10 text-blue-400' },
    info: { icon: <Info size={14} />, text: 'Note', class: 'bg-gray-500/10 text-gray-400' }
  };

  const config = configs[status] || configs.info;

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${config.class}`}>
      {config.icon}
      {config.text}
    </div>
  );
}
