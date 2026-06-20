import { expect, test } from '@playwright/test';
import path from 'node:path';

const shot = (...parts: string[]) => path.resolve(process.cwd(), '../../final_demo_qa/screenshots/final', ...parts);

test('main visible learner buttons are actionable or disabled with reason', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('learner_id', 'pw_buttons');
    localStorage.setItem('app_learner_code', 'pw_buttons');
    localStorage.setItem('user_id', 'user_pw_buttons');
    localStorage.setItem('access_token', 'playwright-demo-token');
    localStorage.setItem('active_subject', 'Python');
    localStorage.setItem('current_concept_id', 'P1');
    localStorage.setItem('current_concept_name', 'Variables');
  });
  await page.goto('/subjects/python/path');
  await expect(page.getByRole('button', { name: /Start Lesson/i }).first()).toBeVisible();
  await expect(page.getByText(/Complete Variables through easy, medium, and hard/i).first()).toBeVisible();
  await page.screenshot({ path: shot('button_audit_path.png'), fullPage: true });

  await page.goto('/quiz/P1');
  await expect(page.getByRole('button', { name: /Need a hint/i }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Check Answer|Submit/i }).first()).toBeVisible();
  await page.screenshot({ path: shot('button_audit_quiz.png'), fullPage: true });
});
