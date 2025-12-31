import tldextract
import re

class DecisionEngine:
    def __init__(self, config_loader):
        self.config = config_loader

    def is_subdomain(self, domain):
        extracted = tldextract.extract(domain)
        # If subdomain part exists and isn't just 'www'
        # Actually checklist says: "CNAME www -> root domain"
        # So 'www' counts as part of root setup usually.
        # But if user enters 'www.example.com', do they mean root?
        # Usually yes.
        # If user enters 'shop.example.com', that's a subdomain.
        if extracted.subdomain and extracted.subdomain != 'www':
            return True
        return False

    def evaluate(self, domain, platform_id, intent, email_state, dns_snapshot):
        is_sub = self.is_subdomain(domain)
        platform_rules = self.config.get_platform(platform_id)
        decision_rules = self.config.get_decision_rules()

        # 1. Determine Identity (Root vs Subdomain)
        warnings = []
        
        # 2. Select Connection Option
        connection_option = None
        
        if is_sub:
             # Subdomain rules
             # "always_use: cname_only" from yaml
             # But let's read the rules
             sub_rules = decision_rules.get('subdomain', {})
             if sub_rules.get('always_use') == 'cname_only':
                 connection_option = 'cname_only'
        else:
            # Root rules
            root_rules = decision_rules.get('root_domain', [])
            # Evaluate "when" conditions
            # supported intent flags in yaml: external_dependencies
            # We need to map our intent dict to the yaml keys.
            
            # Simple evaluator
            for rule in root_rules:
                conditions = rule.get('when', {})
                match = True
                for k, v in conditions.items():
                    # Map yaml key to intent key if needed, or assume 1:1
                    # Yaml keys: external_dependencies
                    # Intent keys: has_external_dependencies
                    
                    intent_val = None
                    if k == 'external_dependencies':
                        intent_val = intent.get('has_external_dependencies')
                    
                    if intent_val != v:
                        match = False
                        break
                
                if match:
                    connection_option = rule.get('use')
                    break
        
        # 3. Validation & Conflicts
        conflicts = []
        
        # Check email conflicts
        if email_state['has_mx']:
            # If we detected MX records, override to record-level changes (option_2)
            # Changing nameservers (option_1) would break existing email
            if connection_option == 'option_1':
                connection_option = 'option_2'
                warnings.append(
                    "Custom email address detected. Please verify with the customer if they "
                    "are using email on this domain. Switching to record-level DNS changes to "
                    "preserve existing email configuration."
                )
            
            mx_warning = self.config.get_warning('mx_present')
            if mx_warning:
                warnings.append(mx_warning['message'])
        
        # Check for strict DMARC policy without MX records (defensive/intentional email blocking)
        if email_state.get('has_dmarc') and not email_state.get('has_mx'):
            dmarc_policy = email_state.get('dmarc_policy')
            if dmarc_policy in ['reject', 'quarantine']:
                warnings.append(
                    f"DMARC is set to p={dmarc_policy}, but no MX records were found. "
                    "This is valid but may be intentional or defensive."
                )

        # Validate current DNS against chosen option
        if connection_option == 'option_1':
            # Option 1: Nameserver-based connection
            # Check if nameservers are already set correctly
            current_ns = dns_snapshot.get('NS', [])
            current_ns_vals = [r.get('value', '').rstrip('.').lower() for r in current_ns]
            required_ns = [ns.rstrip('.').lower() for ns in platform_rules.get('nameservers', [])]
            
            if all(ns in current_ns_vals for ns in required_ns):
                # Already configured correctly
                pass
            elif current_ns_vals and not any(ns in current_ns_vals for ns in required_ns):
                # Different nameservers detected
                conflicts.append({
                    "type": "nameserver_mismatch",
                    "severity": "info",
                    "message": f"Current nameservers ({', '.join(current_ns_vals)}) differ from required nameservers.",
                    "blocking": False
                })
                
        elif connection_option == 'option_2':
            # Option 2: Record-level changes
            # Check for conflicts in A and CNAME records
            root_opts = platform_rules.get('root_domain', {})
            opt_config = root_opts.get('option_2', {})
            required_records = opt_config.get('records', [])
            
            for rec in required_records:
                rec_type = rec['type']
                host = rec['host']
                target_val = rec['value']
                if target_val == "{root_domain}":
                    target_val = domain
                target_val = target_val.rstrip('.').lower()
                
                # Determine the lookup key
                lookup_key = rec_type
                if host == 'www':
                    lookup_key = f"WWW_{rec_type}"
                elif host == '@':
                    lookup_key = rec_type
                
                current_records = dns_snapshot.get(lookup_key, [])
                
                # Check for conflicting record types
                if rec_type == 'CNAME':
                    # If we need CNAME, check if there's a conflicting A record
                    conflicting_key = f"WWW_A" if host == 'www' else "A"
                    conflicting_a = dns_snapshot.get(conflicting_key, [])
                    
                    # FIX: If a CNAME already exists for this host, any A records found
                    # are likely just the results of the resolver following the CNAME chain.
                    # We should only flag a conflict if there is NO CNAME record.
                    has_cname_key = f"WWW_CNAME" if host == 'www' else "CNAME"
                    has_cname = bool(dns_snapshot.get(has_cname_key))
                    
                    if conflicting_a and not has_cname:
                        conflicts.append({
                            "type": "record_conflict",
                            "severity": "warning",
                            "message": f"A record exists for {host}, but CNAME is required. The A record must be removed.",
                            "blocking": True,
                            "conflicting_record": {
                                "type": "A",
                                "host": host,
                                "value": conflicting_a[0].get('value', '')
                            }
                        })
                
                elif rec_type == 'A':
                    # If we need A, check if there's a conflicting CNAME
                    conflicting_key = f"WWW_CNAME" if host == 'www' else "CNAME"
                    conflicting_cname = dns_snapshot.get(conflicting_key, [])
                    
                    # For root (@), any CNAME is a conflict
                    # For www, any CNAME is a conflict if we want an A record
                    if conflicting_cname:
                        conflicts.append({
                            "type": "record_conflict",
                            "severity": "warning",
                            "message": f"CNAME record exists for {host}, but A record is required. The CNAME must be removed.",
                            "blocking": True,
                            "conflicting_record": {
                                "type": "CNAME",
                                "host": host,
                                "value": conflicting_cname[0].get('value', '')
                            }
                        })
                
                # Check if record matches target
                if current_records:
                    matched_records = [r for r in current_records if r.get('value', '').rstrip('.').lower() == target_val]
                    incorrect_records = [r for r in current_records if r.get('value', '').rstrip('.').lower() != target_val]
                    
                    if not matched_records:
                        conflicts.append({
                            "type": "record_mismatch",
                            "severity": "info",
                            "message": f"{rec_type} record for {host} points to incorrect target.",
                            "blocking": False,
                            "current": current_records[0].get('value', ''),
                            "required": target_val
                        })
                    elif incorrect_records:
                        # We have the correct record, but also some incorrect ones
                        for r in incorrect_records:
                            conflicts.append({
                                "type": "extra_record",
                                "severity": "warning",
                                "message": f"Extra {rec_type} record found for {host} ({r.get('value')}). This may cause intermittent connection issues.",
                                "blocking": True, # Extra records should be removed
                                "conflicting_record": r
                            })
        
        # Subdomain-specific validation
        if is_sub:
            sub_config = platform_rules.get('subdomain', {})
            target = sub_config.get('target', '').rstrip('.').lower()
            
            # Check for conflicting A record on subdomain
            # Use the full domain for matching since dns_lookup uses full domain as host
            current_a = [r for r in dns_snapshot.get('A', []) if r.get('host', '').rstrip('.') == domain.rstrip('.')]
            has_sub_cname = any(r.get('host', '').rstrip('.') == domain.rstrip('.') for r in dns_snapshot.get('CNAME', []))
            
            if current_a and not has_sub_cname:
                conflicts.append({
                    "type": "subdomain_a_conflict",
                    "severity": "warning",
                    "message": f"A record exists for subdomain {domain}. It must be removed before adding CNAME.",
                    "blocking": True,
                    "conflicting_record": {
                        "type": "A",
                        "host": domain,
                        "value": current_a[0].get('value', '')
                    }
                })
            
            # Check existing CNAME
            current_cname = [r for r in dns_snapshot.get('CNAME', []) if r.get('host', '').rstrip('.') == domain.rstrip('.')]
            if current_cname:
                cname_val = current_cname[0].get('value', '').rstrip('.').lower()
                if cname_val != target:
                    conflicts.append({
                        "type": "subdomain_cname_mismatch",
                        "severity": "info",
                        "message": f"CNAME for {domain} points to {cname_val} instead of {target}.",
                        "blocking": False,
                        "current": cname_val,
                        "required": target
                    })
        
        # 4. Delegate Access
        delegate_rules = self.config.get_delegate_access_rules()
        recommend_delegate = False
        
        # Check for NameBright (Internal Registrar)
        whois = dns_snapshot.get('WHOIS', {})
        registrar = str(whois.get('registrar', '')).lower()
        ns_records = [str(r.get('value', '')).lower() for r in dns_snapshot.get('NS', [])]
        
        is_namebright = 'namebright' in registrar or any('namebright' in ns for ns in ns_records)
        is_namebright_expired = any(ns in ['expired1.namebrightdns.com', 'expired2.namebrightdns.com'] for ns in ns_records)
        
        if is_namebright:
            if is_namebright_expired:
                warnings.append(
                    "This domain has EXPIRED name servers from NameBright. "
                    "This usually means the domain has expired and will be released soon. "
                    "There is a high chance the customer cancelled their account or failed to complete a transfer, "
                    "but it was almost certainly registered with us at one point."
                )
            else:
                warnings.append(
                    "This domain appears to be registered with NameBright. "
                    "Since AttractWell and GetOiling use NameBright as our domain partner, "
                    "there is a very high chance we registered this domain for you. "
                    "Confirm that the domain has been registered with us before proceeding. AKA, ask Colin and/or Greg."
                )

        # Check conditions
        rec_conditions = delegate_rules.get('recommend_if', [])
        # rec_conditions is a list of dicts in yaml?
        # yaml:
        # recommend_if:
        #   - registrar_unknown: true
        #   - user_uncomfortable_editing_dns: true
        
        # Wait, the yaml structure for recommend_if is a list of dicts?
        # Let's handle it as list of single-key dicts or just a dict
        if isinstance(rec_conditions, list):
             for condition in rec_conditions:
                 for k, v in condition.items():
                     if k == 'registrar_unknown' and intent.get('registrar_known') == False:
                         recommend_delegate = True
                     if k == 'user_uncomfortable_editing_dns' and intent.get('comfortable_editing_dns') == False:
                         recommend_delegate = True
        
        # Don't recommend delegate access if it's internal NameBright
        if is_namebright:
            recommend_delegate = False

        delegate_info = {
            "recommended": recommend_delegate,
            "registrar": registrar if registrar else None,
            "is_internal": is_namebright,
            "instructions": None
        }

        # Return structured decision
        return {
            "domain": domain,
            "platform": platform_id,
            "is_subdomain": is_sub,
            "connection_option": connection_option,
            "warnings": warnings,
            "conflicts": conflicts,
            "delegate_access": delegate_info,
            "email_state": email_state
        }
