import { TestResult } from '../../lib/types';

export default function TestResultsTable({ rows }: { rows: TestResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="text-slate-400"><tr><th>Input</th><th>Expected</th><th>Actual</th><th>Pass</th></tr></thead>
        <tbody>{rows.map((t, i) => <tr key={i} className="border-t border-slate-800"><td className="py-2">{t.input}</td><td>{t.expectedOutput}</td><td>{t.actualOutput}</td><td className={t.passed ? 'text-emerald-400' : 'text-rose-400'}>{t.passed ? 'Yes' : 'No'}</td></tr>)}</tbody>
      </table>
    </div>
  );
}
