export function getStoredSession() {
  return {
    accessToken: localStorage.getItem('access_token') || '',
    userId: localStorage.getItem('user_id') || '',
    learnerId: localStorage.getItem('learner_id') || '',
    appLearnerCode: localStorage.getItem('app_learner_code') || '',
    name: localStorage.getItem('user_name') || '',
    email: localStorage.getItem('user_email') || '',
  };
}

export function hasStoredSession() {
  const session = getStoredSession();
  return Boolean(session.accessToken && session.userId && session.learnerId);
}
