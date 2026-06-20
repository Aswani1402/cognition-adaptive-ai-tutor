const EVENT_KEY = 'cognitutor_frontend_event_log';

export type FrontendEvent = {
  timestamp: string;
  learner_id: string;
  subject: string;
  concept: string;
  route: string;
  action: string;
  module: string;
  status: string;
  summary: string;
};

export function logFrontendEvent(event: Partial<FrontendEvent>) {
  const record: FrontendEvent = {
    timestamp: new Date().toISOString(),
    learner_id: localStorage.getItem('learner_id') || '',
    subject: localStorage.getItem('active_subject') || '',
    concept: localStorage.getItem('current_concept_name') || localStorage.getItem('current_concept_id') || '',
    route: window.location.pathname,
    action: event.action || 'view',
    module: event.module || 'frontend',
    status: event.status || 'success',
    summary: event.summary || '',
    ...event,
  };
  try {
    const existing = JSON.parse(localStorage.getItem(EVENT_KEY) || '[]') as FrontendEvent[];
    localStorage.setItem(EVENT_KEY, JSON.stringify([record, ...existing].slice(0, 200)));
  } catch {
    localStorage.setItem(EVENT_KEY, JSON.stringify([record]));
  }
}

export function readFrontendEvents() {
  try {
    return JSON.parse(localStorage.getItem(EVENT_KEY) || '[]') as FrontendEvent[];
  } catch {
    return [];
  }
}
