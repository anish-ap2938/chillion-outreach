/** API client for Chillion Agents backend */
const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL || "http://localhost:8000";

// ==================== Types ====================

export interface LinkedInDMInput {
  prospect_profile: {
    name: string;
    title?: string;
    company?: string;
    industry?: string;
    about_section?: string;
    recent_posts?: string[];
  };
  conversation_stage: string;
  offer_context: {
    product_name: string;
    value_propositions: string[];
  };
  past_thread_summary?: string;
  product_key?: string;
  template_key?: string;
  custom_message?: string;
}

export interface ChillionProduct {
  key: string;
  name: string;
  short_name: string;
  description: string;
}

export interface Template {
  key: string;
  name: string;
}

export interface LinkedInDMOutput {
  channel: string;
  stage: string;
  persona: string;
  message_type: string;
  message_text: string;
  personalization_notes: string;
  suggested_follow_up_window_days: number;
}

export interface EmailConversationInput {
  prospect_record: {
    id?: number;
    name: string;
    email?: string;
    title?: string;
    company_id?: number;
    problem_category?: string;
    related_product?: string;
  };
  company_context: {
    name: string;
    industry?: string;
    employee_count?: string;
  };
  conversation_stage: string;
  last_email_thread_summary?: string;
  channel_preferences?: Record<string, any>;
  product_key?: string;
  template_key?: string;
  custom_message?: string;
  opt_out_note?: string;
  validate_before_send?: boolean;
}

export interface EmailConversationOutput {
  channel: string;
  subject_line: string;
  body_html: string;
  body_text: string;
  call_to_action: string;
  follow_up_suggestion_days: number;
  variant_label?: string;
}

export interface IntentListenerInput {
  keywords: string[];
  feed_items: Array<{
    url: string;
    text_snippet: string;
    author?: string;
    author_handle?: string;
    platform: string;
    timestamp: string;
    engagement_metrics?: Record<string, any>;
  }>;
}

export interface IntentRecord {
  source_platform: string;
  url: string;
  author_name?: string;
  author_handle?: string;
  company_if_detectable?: string;
  raw_text: string;
  intent_score_one_to_five: number;
  problem_category: string;
  related_product: string;
  urgency_tag?: string;
  notes_for_sales?: string;
}

export interface IntentListenerOutput {
  intent_records: IntentRecord[];
  total_processed: number;
  relevant_count: number;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
  published_date?: string;
  platform: string;
}

export interface IntentSearchResponse {
  success: boolean;
  query: string;
  results: SearchResult[];
  total_results: number;
  sources: string[];
}

export interface ProspectCSV {
  name: string;
  email?: string;
  company?: string;
  title?: string;
  linkedin_url?: string;
  industry?: string;
  notes?: string;
}

export interface CSVUploadResponse {
  success: boolean;
  message: string;
  total_rows: number;
  imported: number;
  skipped: number;
  errors: string[];
  prospects: ProspectCSV[];
}

export interface GmailStatus {
  connected: boolean;
  email?: string;
  message: string;
}

export interface EmailDraft {
  id?: string;
  to: string;
  subject: string;
  body_text: string;
  body_html?: string;
  status?: string;
}

// ==================== Products & Templates APIs ====================

/** Get available Chillion products */
export async function getProducts(): Promise<ChillionProduct[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/products`);
  if (!response.ok) throw new Error(`Failed to fetch products: ${response.statusText}`);
  return response.json();
}

/** Get available email templates */
export async function getEmailTemplates(): Promise<Template[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/email-templates`);
  if (!response.ok) throw new Error(`Failed to fetch email templates: ${response.statusText}`);
  return response.json();
}

/** Get available LinkedIn templates */
export async function getLinkedInTemplates(): Promise<Template[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/linkedin-templates`);
  if (!response.ok) throw new Error(`Failed to fetch LinkedIn templates: ${response.statusText}`);
  return response.json();
}

// ==================== Agent APIs ====================

/** Generate LinkedIn DM */
export async function generateLinkedInDM(input: LinkedInDMInput): Promise<LinkedInDMOutput> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/linkedin-dm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`LinkedIn DM generation failed: ${response.statusText}`);
  return response.json();
}

/** Generate Email */
export async function generateEmail(input: EmailConversationInput): Promise<EmailConversationOutput> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/email-conversation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Email generation failed: ${response.statusText}`);
  return response.json();
}

/** Process Intent Signals */
export async function processIntent(input: IntentListenerInput): Promise<IntentListenerOutput> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/agents/intent-listener`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Intent processing failed: ${response.statusText}`);
  return response.json();
}

// ==================== Intent Search APIs ====================

/** Search web for intent signals */
export async function searchIntentSignals(keywords: string[], timeRange: string = "24h"): Promise<IntentSearchResponse> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/intent/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keywords, time_range: timeRange, max_results: 20 }),
  });
  if (!response.ok) throw new Error(`Intent search failed: ${response.statusText}`);
  return response.json();
}

/** Get trending topics */
export async function getTrendingTopics() {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/intent/trending`);
  if (!response.ok) throw new Error(`Failed to get trending: ${response.statusText}`);
  return response.json();
}

/** Get keyword suggestions */
export async function getKeywordSuggestions() {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/intent/keywords/suggestions`);
  if (!response.ok) throw new Error(`Failed to get suggestions: ${response.statusText}`);
  return response.json();
}

// ==================== CSV Upload APIs ====================

/** Upload CSV file */
export async function uploadCSV(file: File): Promise<CSVUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${AGENTS_API_URL}/api/v1/csv/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(`CSV upload failed: ${response.statusText}`);
  return response.json();
}

/** Get CSV template */
export async function getCSVTemplate(): Promise<string> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/csv/template`);
  if (!response.ok) throw new Error(`Failed to get template: ${response.statusText}`);
  return response.text();
}

// ==================== Gmail APIs ====================

/** Get Gmail connection status */
export async function getGmailStatus(): Promise<GmailStatus> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/gmail/status`);
  if (!response.ok) throw new Error(`Failed to get Gmail status: ${response.statusText}`);
  return response.json();
}

/** Get Gmail OAuth URL */
export async function getGmailAuthUrl(): Promise<{ auth_url: string }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/gmail/connect`);
  if (!response.ok) throw new Error(`Failed to get auth URL: ${response.statusText}`);
  return response.json();
}

/** Create Gmail drafts */
export async function createGmailDrafts(drafts: EmailDraft[]): Promise<{ success: boolean; created: number; failed: number; drafts: EmailDraft[] }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/gmail/drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drafts }),
  });
  if (!response.ok) throw new Error(`Failed to create drafts: ${response.statusText}`);
  return response.json();
}

/** Disconnect Gmail */
export async function disconnectGmail(): Promise<{ success: boolean }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/gmail/disconnect`, { method: "POST" });
  if (!response.ok) throw new Error(`Failed to disconnect: ${response.statusText}`);
  return response.json();
}

// ==================== Prospect APIs ====================

/** Get Prospects from Agents API */
export async function getProspects() {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/prospects`);
  if (!response.ok) throw new Error(`Failed to fetch prospects: ${response.statusText}`);
  return response.json();
}

/** Create Prospect */
export async function createProspect(data: any) {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/prospects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Failed to create prospect: ${response.statusText}`);
  return response.json();
}

// ==================== Saved Prospects APIs (Persistent Storage) ====================

export interface SavedProspect {
  id: number;
  name: string;
  email?: string;
  company?: string;
  title?: string;
  linkedin_url?: string;
  industry?: string;
  notes?: string;
  source?: string;
  created_at: string;
}

/** Get all saved prospects */
export async function getSavedProspects(): Promise<SavedProspect[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/saved-prospects/`);
  if (!response.ok) throw new Error(`Failed to fetch saved prospects: ${response.statusText}`);
  return response.json();
}

/** Save a prospect to database */
export async function saveProspect(prospect: Omit<ProspectCSV, 'id'> & { source?: string }): Promise<SavedProspect> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/saved-prospects/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prospect),
  });
  if (!response.ok) throw new Error(`Failed to save prospect: ${response.statusText}`);
  return response.json();
}

/** Save multiple prospects to database */
export async function saveProspectsBulk(prospects: Array<Omit<ProspectCSV, 'id'> & { source?: string }>): Promise<{ success: boolean; created: number; errors: string[] }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/saved-prospects/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prospects }),
  });
  if (!response.ok) throw new Error(`Failed to save prospects: ${response.statusText}`);
  return response.json();
}

/** Delete a saved prospect */
export async function deleteSavedProspect(id: number): Promise<{ success: boolean }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/saved-prospects/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Failed to delete prospect: ${response.statusText}`);
  return response.json();
}

/** Delete all saved prospects */
export async function deleteAllSavedProspects(): Promise<{ success: boolean }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/saved-prospects/`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Failed to delete prospects: ${response.statusText}`);
  return response.json();
}

// ==================== Calendly APIs ====================

export interface CalendlyUser {
  uri: string;
  name: string;
  email: string;
  scheduling_url: string;
  timezone: string;
  avatar_url?: string;
}

export interface CalendlyStatus {
  connected: boolean;
  user?: CalendlyUser;
  message: string;
}

export interface CalendlyEvent {
  uri: string;
  name: string;
  status: string;
  start_time: string;
  end_time: string;
  event_type: string;
  location?: string;
  invitee_name?: string;
  invitee_email?: string;
  invitee_company?: string;
  created_at: string;
  cancel_url?: string;
  reschedule_url?: string;
}

export interface CalendlyEventType {
  uri: string;
  name: string;
  slug: string;
  duration_minutes: number;
  scheduling_url: string;
  active: boolean;
  color?: string;
  description?: string;
}

export interface MeetingStats {
  upcoming_count: number;
  today_count: number;
  this_week_count: number;
  past_30_days_count: number;
}

/** Get Calendly connection status */
export async function getCalendlyStatus(): Promise<CalendlyStatus> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/status`);
  if (!response.ok) throw new Error(`Failed to get Calendly status: ${response.statusText}`);
  return response.json();
}

/** Get Calendly event types */
export async function getCalendlyEventTypes(): Promise<CalendlyEventType[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/event-types`);
  if (!response.ok) throw new Error(`Failed to get event types: ${response.statusText}`);
  return response.json();
}

/** Get upcoming meetings */
export async function getUpcomingMeetings(days: number = 30): Promise<CalendlyEvent[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/meetings/upcoming?days=${days}`);
  if (!response.ok) throw new Error(`Failed to get upcoming meetings: ${response.statusText}`);
  return response.json();
}

/** Get past meetings */
export async function getPastMeetings(days: number = 30): Promise<CalendlyEvent[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/meetings/past?days=${days}`);
  if (!response.ok) throw new Error(`Failed to get past meetings: ${response.statusText}`);
  return response.json();
}

/** Get today's meetings */
export async function getTodayMeetings(): Promise<CalendlyEvent[]> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/meetings/today`);
  if (!response.ok) throw new Error(`Failed to get today's meetings: ${response.statusText}`);
  return response.json();
}

/** Get meeting statistics */
export async function getMeetingStats(): Promise<MeetingStats> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/calendly/stats`);
  if (!response.ok) throw new Error(`Failed to get meeting stats: ${response.statusText}`);
  return response.json();
}

// ==================== Lead Generation APIs ====================

export interface SocialLead {
  id: string;
  platform: string;
  url: string;
  author_username?: string;
  author_display_name?: string;
  author_company?: string;
  author_title?: string;
  author_followers?: number;
  title?: string;
  text: string;
  text_excerpt?: string;
  intent_score: number;
  intent_level: string;
  intent_keywords_matched?: string[];
  product_keywords_matched?: string[];
   reason_for_relevance?: string;
  created_at?: string;
  discovered_at?: string;
  source_meta?: Record<string, any>;
}

export interface SocialSearchRequest {
  platforms: string[];
  keywords?: string[];
  max_results?: number;
}

export interface SocialSearchResponse {
  success: boolean;
  total_results: number;
  high_intent_count: number;
  leads: SocialLead[];
  platforms_searched: string[];
  search_timestamp: string;
}

export interface CompanyDiscoveryRequest {
  company_names: string[];
  discover_websites?: boolean;
  enrich?: boolean;
}

export interface DiscoveredCompany {
  id?: string;
  name: string;
  domain?: string;
  website?: string;
  industry?: string;
  employee_count?: number;
  employee_range?: string;
  revenue_usd?: number;
  revenue_range?: string;
  headquarters_city?: string;
  headquarters_state?: string;
  headquarters_country?: string;
  linkedin_url?: string;
  is_target_profile: boolean;
  target_score: number;
  discovered_at?: string;
}

export interface CompanyDiscoveryResponse {
  success: boolean;
  total_found: number;
  target_matches: number;
  companies: DiscoveredCompany[];
}

export interface ContactDiscoveryRequest {
  company_name: string;
  company_domain?: string;
  company_website?: string;
}

export interface DiscoveredContact {
  id?: string;
  company_name: string;
  company_domain?: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  title: string;
  email?: string;
  email_status?: string;
  linkedin_url?: string;
  seniority_level?: string;
  source_url?: string;
  discovered_at?: string;
}

export interface ContactDiscoveryResponse {
  success: boolean;
  company_name: string;
  contacts_found: number;
  contacts: DiscoveredContact[];
}

export interface EmailGenerateRequest {
  first_name: string;
  last_name: string;
  company_domain: string;
  num_patterns?: number;
}

export interface EmailCandidate {
  email: string;
  pattern_used: string;
  confidence: number;
  is_validated: boolean;
  validation_result?: string;
}

export interface EmailGenerateResponse {
  success: boolean;
  contact_name: string;
  company_domain: string;
  best_guess?: string;
  candidates: EmailCandidate[];
}

export interface LeadGenStats {
  total_social_leads: number;
  high_intent_leads: number;
  total_companies: number;
  target_companies: number;
  total_contacts: number;
  contacts_with_email: number;
}

export interface LeadGenConfig {
  intent_keywords: string[];
  product_keywords: string[];
  reddit_subreddits: string[];
  target_industries: string[];
  target_titles: string[];
  min_revenue_usd: number;
  search_provider?: "dummy" | "serpapi" | "google_cse";
  enable_serpapi?: boolean;
  enable_google_cse?: boolean;
  has_serpapi_key?: boolean;
  has_google_cse?: boolean;
}

export interface LeadGenMetrics {
  request_count: number;
  error_count: number;
  high_intent_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  samples: number;
}

/** Search social media for buying intent signals */
export async function searchSocialMedia(request: SocialSearchRequest): Promise<SocialSearchResponse> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/social/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Social search failed: ${response.statusText}`);
  return response.json();
}

/** Get stored social leads */
export async function getSocialLeads(params?: { platform?: string; min_intent?: number; since_days?: number; limit?: number; offset?: number; sort_by?: string; sort_order?: "asc" | "desc" }): Promise<{ success: boolean; count: number; leads: SocialLead[] }> {
  const query = new URLSearchParams();
  if (params?.platform) query.set("platform", params.platform);
  if (params?.min_intent !== undefined) query.set("min_intent", params.min_intent.toString());
  if (params?.since_days !== undefined) query.set("since_days", params.since_days.toString());
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset !== undefined) query.set("offset", params.offset.toString());
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.sort_order) query.set("sort_order", params.sort_order);
  
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/social/leads?${query}`);
  if (!response.ok) throw new Error(`Failed to get leads: ${response.statusText}`);
  return response.json();
}

/** Discover companies */
export async function discoverCompanies(request: CompanyDiscoveryRequest): Promise<CompanyDiscoveryResponse> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/companies/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Company discovery failed: ${response.statusText}`);
  return response.json();
}

/** Get stored companies */
export async function getDiscoveredCompanies(params?: { industry?: string; is_target?: boolean; limit?: number; offset?: number; sort_by?: string; sort_order?: "asc" | "desc" }): Promise<{ success: boolean; count: number; companies: DiscoveredCompany[] }> {
  const query = new URLSearchParams();
  if (params?.industry) query.set("industry", params.industry);
  if (params?.is_target !== undefined) query.set("is_target", params.is_target.toString());
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset !== undefined) query.set("offset", params.offset.toString());
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.sort_order) query.set("sort_order", params.sort_order);
  
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/companies?${query}`);
  if (!response.ok) throw new Error(`Failed to get companies: ${response.statusText}`);
  return response.json();
}

/** Discover contacts for a company */
export async function discoverContacts(request: ContactDiscoveryRequest): Promise<ContactDiscoveryResponse> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/contacts/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Contact discovery failed: ${response.statusText}`);
  return response.json();
}

/** Get stored contacts */
export async function getDiscoveredContacts(params?: { company?: string; seniority?: string; has_email?: boolean; limit?: number; offset?: number; sort_by?: string; sort_order?: "asc" | "desc" }): Promise<{ success: boolean; count: number; contacts: DiscoveredContact[] }> {
  const query = new URLSearchParams();
  if (params?.company) query.set("company", params.company);
  if (params?.seniority) query.set("seniority", params.seniority);
  if (params?.has_email !== undefined) query.set("has_email", params.has_email.toString());
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset !== undefined) query.set("offset", params.offset.toString());
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.sort_order) query.set("sort_order", params.sort_order);
  
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/contacts?${query}`);
  if (!response.ok) throw new Error(`Failed to get contacts: ${response.statusText}`);
  return response.json();
}

/** Generate email address candidates */
export async function generateEmailCandidates(request: EmailGenerateRequest): Promise<EmailGenerateResponse> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/email/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Email generation failed: ${response.statusText}`);
  return response.json();
}

/** Get lead generation statistics */
export async function getLeadGenStats(): Promise<LeadGenStats> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/stats`);
  if (!response.ok) throw new Error(`Failed to get stats: ${response.statusText}`);
  return response.json();
}

/** Get lead generation configuration */
export async function getLeadGenConfig(): Promise<LeadGenConfig> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/config`);
  if (!response.ok) throw new Error(`Failed to get config: ${response.statusText}`);
  return response.json();
}

/** Update search provider (serpapi, google_cse, dummy) */
export async function setSearchProvider(provider: "serpapi" | "google_cse" | "dummy"): Promise<{ success: boolean; search_provider: string }> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/config/search-provider`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  if (!response.ok) throw new Error(`Failed to update search provider: ${response.statusText}`);
  return response.json();
}

/** Get lead generation metrics */
export async function getLeadGenMetrics(): Promise<LeadGenMetrics> {
  const response = await fetch(`${AGENTS_API_URL}/api/v1/lead-gen/metrics`);
  if (!response.ok) throw new Error(`Failed to get metrics: ${response.statusText}`);
  return response.json();
}

