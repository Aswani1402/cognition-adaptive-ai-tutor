import { expect, test } from '@playwright/test';
import path from 'node:path';

const screenshots = (...parts: string[]) => path.resolve(process.cwd(), '../../final_demo_qa/screenshots/final', ...parts);

async function seedSession(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    const learnerId = `pw_final_${Date.now()}`;
    localStorage.setItem('learner_id', learnerId);
    localStorage.setItem('app_learner_code', learnerId);
    localStorage.setItem('user_id', `user_${Date.now()}`);
    localStorage.setItem('access_token', 'playwright-demo-token');
    localStorage.setItem('user_name', 'Final Demo Learner');
    localStorage.setItem('user_email', 'final.demo@example.com');
    localStorage.setItem('active_subject', 'Python');
    localStorage.setItem('current_concept_id', 'P1');
    localStorage.setItem('current_concept_name', 'Variables');
    localStorage.setItem('current_difficulty', 'easy');
  });
}

test.describe('final demo learner flow', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page);
  });

  test('learning path locks future concepts', async ({ page }) => {
    await page.goto('/subjects/python/path');
    await expect(page.getByText(/Variables/i).first()).toBeVisible();
    await expect(page.getByText(/Data Types/i).first()).toBeVisible();
    await expect(page.getByText(/Complete Variables through easy, medium, and hard/i).first()).toBeVisible();
    const lockedStartButtons = page.getByRole('button', { name: /Start Lesson/i }).filter({ hasText: /Start Lesson/i });
    await expect(lockedStartButtons.first()).toBeVisible();
    await page.screenshot({ path: screenshots('02_learning_path_locking.png'), fullPage: true });
  });

  test('teaching views are visible and distinct', async ({ page }) => {
    await page.goto('/lesson/P1');
    for (const label of ['Explanation', 'Definition', 'Example', 'Step-by-step', 'Debug', 'Predict output', 'Transfer', 'Challenge', 'Revision', 'Compare', 'Real world']) {
      await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
    }
    await page.screenshot({ path: screenshots('03_teaching_views.png'), fullPage: true });
  });

  test('MCQ renders options instead of textarea', async ({ page, request }) => {
    const response = await request.get('http://127.0.0.1:8000/assessment/pw_final/P1?subject=Python&difficulty=easy');
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    const questions = body.questions || body.assessment || body.data?.questions || [];
    const mcq = questions.find((q: any) => (q.task_type || q.taskType || q.question_type) === 'mcq');
    expect(mcq).toBeTruthy();
    expect(mcq.options?.length).toBe(4);
    await page.goto('/quiz/P1');
    await expect(page.getByText(/Which statement best explains/i).first()).toBeVisible();
    await expect(page.getByRole('button').filter({ hasText: /unrelated|memorized|deployment|Variables/i }).first()).toBeVisible();
    const card = page.locator('[data-testid="question-card"], article, section').filter({ hasText: /Which statement best explains/i }).first();
    await expect(card.locator('textarea')).toHaveCount(0);
    await page.screenshot({ path: screenshots('04_mcq_options.png'), fullPage: true });
  });

  test('notebook opens structured page', async ({ page }) => {
    await page.goto('/notebook');
    for (const label of ['Quick Summary', 'Key Points', 'Common Mistakes', 'Revision Plan']) {
      await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
    }
    const repeated = await page.getByText('Notebook summary for Variables').count();
    expect(repeated).toBeLessThan(2);
    await page.screenshot({ path: screenshots('08_notebook_structured.png'), fullPage: true });
  });
});
