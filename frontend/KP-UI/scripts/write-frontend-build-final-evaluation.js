import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const outJson = path.join(root, 'outputs', 'final_evaluation', 'json', 'frontend_build_final_evaluation.json');
const outMd = path.join(root, 'outputs', 'final_evaluation', 'reports', 'frontend_build_final_evaluation.md');
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const buildStatus = process.env.FRONTEND_BUILD_STATUS || 'WARN';
const lintStatus = process.env.FRONTEND_LINT_STATUS || (packageJson.scripts?.lint ? 'WARN' : 'WARN');
const buildOutput = process.env.FRONTEND_BUILD_OUTPUT || '';
const lintOutput = process.env.FRONTEND_LINT_OUTPUT || '';
const report = {
  evaluation_name: 'frontend_build_final_evaluation',
  status: buildStatus === 'PASS' && (lintStatus === 'PASS' || lintStatus === 'WARN') ? 'PASS' : (buildStatus === 'PASS' ? 'WARN' : 'FAIL'),
  build_status: buildStatus,
  lint_status: lintStatus,
  lint_reason: packageJson.scripts?.lint ? null : 'npm run lint script missing',
  build_command: 'npm run build',
  lint_command: packageJson.scripts?.lint ? 'npm run lint' : null,
  build_output_tail: buildOutput.slice(-4000),
  lint_output_tail: lintOutput.slice(-4000),
};
fs.mkdirSync(path.dirname(outJson), { recursive: true });
fs.mkdirSync(path.dirname(outMd), { recursive: true });
fs.writeFileSync(outJson, JSON.stringify(report, null, 2), 'utf8');
fs.writeFileSync(
  outMd,
  `# Frontend Build Final Evaluation\n\n- status: ${report.status}\n- build_status: ${buildStatus}\n- lint_status: ${lintStatus}\n- lint_reason: ${report.lint_reason || 'none'}\n`,
  'utf8',
);
console.log(JSON.stringify({ status: report.status, json: outJson }, null, 2));
