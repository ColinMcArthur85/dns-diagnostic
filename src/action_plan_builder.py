class ActionPlanBuilder:
    def __init__(self, config_loader):
        self.config = config_loader


    def _is_record_match(self, dns_snapshot, rec_type, host, target_value, domain):
        """Checks if the required record is already present in the DNS snapshot."""
        # Determine the key to look for in dns_snapshot
        lookup_key = rec_type
        if host == "www":
            if rec_type == "CNAME":
                lookup_key = "WWW_CNAME"
            elif rec_type == "A":
                lookup_key = "WWW_A"
        
        records = dns_snapshot.get(lookup_key, [])
        target = target_value.rstrip('.').lower()
        
        for r in records:
            current_val = r.get('value', '').rstrip('.').lower()
            if current_val == target:
                return True
        return False

    def _build_comparison(self, decision, dns_snapshot, platform_rules, option_key):
        comparison = []
        is_sub = decision['is_subdomain']
        
        # 1. Nameservers (Always show if NS or WHOIS present)
        current_ns = dns_snapshot.get('NS', [])
        current_ns_vals = [r.get('value', '').rstrip('.').lower() for r in current_ns]
        whois_ns = dns_snapshot.get('WHOIS', {}).get('name_servers', [])
        all_current_ns = list(set(current_ns_vals + [ns.rstrip('.').lower() for ns in whois_ns]))
        
        target_ns = [ns.rstrip('.').lower() for ns in platform_rules.get('nameservers', [])]
        
        ns_status = "missing"
        if option_key == 'option_1':
            ns_status = "matched" if all(ns in all_current_ns for ns in target_ns) else "different"
        elif all(ns in all_current_ns for ns in target_ns):
            ns_status = "matched"
        else:
            ns_status = "external"

        comparison.append({
            "label": "Nameservers",
            "current": ", ".join(all_current_ns) if all_current_ns else "None detected",
            "target": ", ".join(target_ns),
            "status": ns_status,
            "is_required": False,
            "is_recommended": (option_key == 'option_1')
        })

        # 2. Main Connection Records
        if is_sub:
            import tldextract
            extracted = tldextract.extract(decision['domain'])
            host = extracted.subdomain
            sub_config = platform_rules.get('subdomain', {})
            target = sub_config.get('target')
            
            # Only show if CNAME was queried
            if 'CNAME' in dns_snapshot or 'WWW_CNAME' in dns_snapshot:
                exists = self._is_record_match(dns_snapshot, "CNAME", host, target, decision['domain'])
                current_cnames = [r.get('value', '').rstrip('.') for r in dns_snapshot.get('CNAME', []) if r.get('host') == host]
                status = "matched" if exists else ("conflict" if current_cnames else "missing")
                
                comparison.append({
                    "label": f"CNAME ({host})",
                    "current": ", ".join(current_cnames) if current_cnames else "None detected",
                    "target": target,
                    "status": status,
                    "is_required": True
                })
        else:
            root_opts = platform_rules.get('root_domain', {})
            opt_2_config = root_opts.get('option_2', {})
            records = opt_2_config.get('records', [])
            
            for rec in records:
                # Only show if this type was queried
                lookup_key = rec['type']
                if rec['host'] == 'www':
                    lookup_key = f"WWW_{rec['type']}"
                
                if lookup_key in dns_snapshot or rec['type'] in dns_snapshot:
                    val = rec['value']
                    if val == "{root_domain}":
                        val = decision['domain']
                    
                    exists = self._is_record_match(dns_snapshot, rec['type'], rec['host'], val, decision['domain'])
                    current_records = dns_snapshot.get(lookup_key, [])
                    current_vals = [r.get('value', '').rstrip('.') for r in current_records]
                    status = "matched" if exists else ("conflict" if current_vals else "missing")
                    
                    comparison.append({
                        "label": f"{rec['type']} Record ({rec['host']})",
                        "current": ", ".join(current_vals) if current_vals else "None detected",
                        "target": val,
                        "status": status,
                        "is_required": True
                    })

        # 3. Email Records
        if 'MX' in dns_snapshot:
            mx_recs = dns_snapshot.get('MX', [])
            comparison.append({
                "label": "MX Records",
                "current": ", ".join([f"{r.get('value')} (prio {r.get('priority', '?')})" for r in mx_recs]) if mx_recs else "None",
                "target": "Preserve existing",
                "status": "matched" if mx_recs else "info",
                "is_required": False
            })

        if 'TXT' in dns_snapshot:
            spf = decision.get('email_state', {}).get('spf_record')
            comparison.append({
                "label": "SPF Record",
                "current": spf if spf else "None detected",
                "target": "Preserve existing",
                "status": "matched" if spf else "info",
                "is_required": False
            })
        
        # 4. Diagnostics
        if 'DMARC' in dns_snapshot:
            dmarc = decision.get('email_state', {}).get('dmarc_record')
            comparison.append({
                "label": "DMARC Record",
                "current": dmarc if dmarc else "None detected",
                "target": "p=quarantine (Recommended)",
                "status": "matched" if dmarc else "info",
                "is_required": False
            })

        if 'DKIM' in dns_snapshot:
            dkim_found = decision.get('email_state', {}).get('dkim_detected', False)
            dkim_val = decision.get('email_state', {}).get('dkim_record')
            comparison.append({
                "label": "DKIM Records",
                "current": (dkim_val[:50] + "...") if dkim_val else ("Detected" if dkim_found else "None detected"),
                "target": "Add if available",
                "status": "matched" if dkim_found else "info",
                "is_required": False
            })
        
        return comparison

    def _was_record_queried(self, rec_type, host, queried_sections):
        if not queried_sections or 'all' in queried_sections:
            return True
        
        # Map sections to record types (matching dns_lookup.py)
        mapping = {
            'web': ['A', 'CNAME', 'NS'],
            'email': ['MX', 'TXT', 'DMARC', 'DKIM'],
            'SPF': ['TXT']
        }
        
        for section in queried_sections:
            if section == rec_type:
                return True
            if section in mapping and rec_type in mapping[section]:
                return True
        return False

    def build_plan(self, decision, dns_snapshot, email_state):
        queried_sections = decision.get('intent', {}).get('queried_sections')
        
        plan = {
            "domain": decision['domain'],
            "platform": decision['platform'],
            "is_subdomain": decision['is_subdomain'],
            "dns_snapshot": dns_snapshot,
            "email_state": email_state,
            "connection_option": decision['connection_option'],
            "warnings": decision['warnings'],
            "delegate_access": decision['delegate_access'],
            "recommended_actions": [],
            "potential_issues": [], # For records not queried but potentially missing
            "comparison": [],
            "is_completed": False,
            "status_message": "Domain requires configuration."
        }

        # Resolve actions
        platform_rules = self.config.get_platform(decision['platform'])
        option_key = decision['connection_option']
        
        if not option_key:
             plan['warnings'].append("No valid connection option found for this scenario.")
             return plan

        # Build comparison table data
        plan['comparison'] = self._build_comparison(decision, dns_snapshot, platform_rules, option_key)

        actions = []
        suggestions = []
        
        if decision['is_subdomain']:
            import tldextract
            extracted = tldextract.extract(decision['domain'])
            host = extracted.subdomain
            sub_config = platform_rules.get('subdomain', {})
            target = sub_config.get('target')
            
            if not self._is_record_match(dns_snapshot, "CNAME", host, target, decision['domain']):
                action = {
                    "action": "add_record",
                    "type": "CNAME",
                    "host": host,
                    "value": target
                }
                if self._was_record_queried('CNAME', host, queried_sections):
                    actions.append(action)
                else:
                    suggestions.append(action)
        else:
            if option_key == 'option_1':
                # Nameserver change
                ns_list = platform_rules.get('nameservers', [])
                current_ns = dns_snapshot.get('NS', [])
                current_ns_vals = [r.get('value', '').rstrip('.').lower() for r in current_ns]
                needed_ns = [ns.rstrip('.').lower() for ns in ns_list]
                
                is_match = all(ns in current_ns_vals for ns in needed_ns) if needed_ns else False
                
                if not is_match:
                    action = {
                        "action": "change_nameservers",
                        "values": ns_list
                    }
                    if self._was_record_queried('NS', '@', queried_sections):
                        actions.append(action)
                    else:
                        suggestions.append(action)
            
            elif option_key == 'option_2':
                # Record level
                root_opts = platform_rules.get('root_domain', {})
                opt_config = root_opts.get('option_2', {})
                
                records = opt_config.get('records', [])
                for rec in records:
                    val = rec['value']
                    if val == "{root_domain}":
                        val = decision['domain']
                    
                    if not self._is_record_match(dns_snapshot, rec['type'], rec['host'], val, decision['domain']):
                        action = {
                            "action": "add_record",
                            "type": rec['type'],
                            "host": rec['host'],
                            "value": val
                        }
                        if self._was_record_queried(rec['type'], rec['host'], queried_sections):
                            actions.append(action)
                        else:
                            suggestions.append(action)

        plan['recommended_actions'] = actions
        plan['potential_issues'] = suggestions
        
        if not actions:
            plan['is_completed'] = True
            platform_id = platform_rules.get('id', decision['platform']).upper()
            
            if queried_sections and 'all' not in queried_sections:
                sections_str = ", ".join(queried_sections)
                plan['status_message'] = f"The requested {sections_str} records are correctly configured."
            else:
                plan['status_message'] = f"This domain is connected to {platform_id}, and is completed."
            
        return plan
