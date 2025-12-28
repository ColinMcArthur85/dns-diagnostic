"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Shield, Info, ArrowRight, CheckCircle, AlertTriangle, Terminal, Globe, Mail } from 'lucide-react';

export default function Home() {
  const [domain, setDomain] = useState('');
  const [platform, setPlatform] = useState('attractwell');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [selectedSections, setSelectedSections] = useState<string[]>(['all']);
  const [error, setError] = useState<string | null>(null);

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
        body: JSON.stringify({ domain, platform, sections: selectedSections }),
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
          The ultimate engine for analyzing domain salud and connectivity settings.
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

            {/* AI Analysis Section */}
            {result.ai_insights?.summary && (
              <div className="insight-panel">
                <div className="panel-label text-blue-400">
                  <Terminal size={14} />
                  AI Analysis
                </div>
                <div className="text-gray-300 leading-relaxed text-sm font-mono whitespace-pre-wrap">
                  {result.ai_insights.summary}
                </div>
              </div>
            )}

            {/* Next Steps Section */}
            {result.ai_insights?.next_steps && Array.isArray(result.ai_insights.next_steps) && (
              <div className="info-panel">
                <h3 className="text-blue-400 font-bold mb-6 flex items-center gap-2">
                  <ArrowRight size={20} />
                  Recommended Next Steps
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {result.ai_insights.next_steps.map((step: string, i: number) => (
                    <div key={i} className="flex items-start gap-4 p-4 bg-[#161616]/50 border border-[#262626] rounded-xl">
                      <div className="w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold shrink-0">
                        {i + 1}
                      </div>
                      <p className="text-gray-300 text-sm leading-relaxed">{step}</p>
                    </div>
                  ))}
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
                <div className="card-body space-y-4">
                  {result.recommended_actions.map((action: any, idx: number) => (
                    <div key={idx} className="action-item">
                      <div className="action-number">
                        {idx + 1}
                      </div>
                      <div>
                        {action.action === 'change_nameservers' ? (
                          <>
                            <div className="font-semibold text-gray-200">Update Nameservers</div>
                            <div className="font-mono text-sm text-gray-500 whitespace-pre-wrap">
                              Set nameservers to: <span className="text-blue-300">{Array.isArray(action.values) ? action.values.join(', ') : action.values}</span>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="font-semibold text-gray-200">{action.type} Record</div>
                            <div className="font-mono text-sm text-gray-500">
                              Host: <span className="text-blue-300">{action.host}</span> → Value: <span className="text-purple-300">{action.value}</span>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </main>
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
