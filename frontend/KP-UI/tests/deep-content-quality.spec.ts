import { expect, test } from '@playwright/test';
import path from 'node:path';

const shot = (...parts: string[]) => path.resolve(process.cwd(), '../../final_demo_qa/screenshots/deep_content', ...parts);

test('backend-generated content and task quality are valid', async ({ page, request }) => {
  const lesson = await request.get('http://127.0.0.1:8000/lesson/pw_deep/P1?subject=Python&difficulty=easy');
  expect(lesson.ok()).toBeTruthy();
  const lessonJson = await lesson.json();
  const views = lessonJson.content_by_view || lessonJson.data?.content_by_view || {};
  const expectedViews = [
    'explanation',
    'definition_view',
    'simple_example_view',
    'step_by_step_view',
    'analogy_view',
    'code_view',
    'misconception_view',
    'debug_view',
    'output_prediction_view',
    'transfer_view',
    'challenge_view',
    'revision_summary_view',
    'comparison_view',
    'real_world_connection_view',
  ];
  for (const view of expectedViews) {
    expect(String(views[view]?.explanation || '')).toMatch(/variable|Variables/i);
  }
  expect(new Set(expectedViews.map((view) => views[view]?.explanation)).size).toBe(expectedViews.length);

  const assessment = await request.get('http://127.0.0.1:8000/assessment/pw_deep/P1?subject=Python&difficulty=hard');
  expect(assessment.ok()).toBeTruthy();
  const assessmentJson = await assessment.json();
  const questions = assessmentJson.questions || assessmentJson.assessment || assessmentJson.data?.questions || [];
  expect(questions.length).toBeGreaterThan(5);
  const byType = new Map<string, any>(questions.map((q: any) => [q.task_type || q.taskType || q.question_type, q]));
  expect(byType.get('mcq')?.options?.length).toBe(4);
  expect(byType.get('output_prediction')?.code || byType.get('output_prediction')?.starter_code).toBeTruthy();
  expect(byType.get('debug_task')?.buggy_code || byType.get('debug_task')?.buggyCode).toBeTruthy();
  expect(byType.get('coding_question')?.prompt || byType.get('coding_prompt')?.prompt).toMatch(/write|program|query|snippet|command/i);
  expect(byType.get('challenge_question')?.prompt).not.toEqual(byType.get('puzzle')?.prompt);

  await page.addInitScript(() => {
    localStorage.setItem('learner_id', 'pw_deep');
    localStorage.setItem('app_learner_code', 'pw_deep');
    localStorage.setItem('user_id', 'user_pw_deep');
    localStorage.setItem('access_token', 'playwright-demo-token');
    localStorage.setItem('active_subject', 'Python');
    localStorage.setItem('current_concept_id', 'P1');
    localStorage.setItem('current_concept_name', 'Variables');
    localStorage.setItem('current_difficulty', 'easy');
  });
  await page.goto('/lesson/P1');
  await expect(page.getByText(/Variables/i).first()).toBeVisible();
  await page.screenshot({ path: shot('lesson_views.png'), fullPage: true });
});
