import { CodeRunOutput } from '../../lib/types';

export default function RunOutputPanel({ output }: { output: CodeRunOutput['runOutput'] }) {
  const stdout = output.stdout && output.stdout.trim() ? output.stdout : 'No stdout output';
  const stderr = output.stderr && output.stderr.trim() ? output.stderr : 'No errors';
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <div className="rounded-lg border border-slate-800 p-3"><div className="text-xs uppercase text-slate-500">stdout</div><pre className="whitespace-pre-wrap text-emerald-300">{stdout}</pre></div>
      <div className="rounded-lg border border-slate-800 p-3"><div className="text-xs uppercase text-slate-500">stderr</div><pre className="whitespace-pre-wrap text-rose-300">{stderr}</pre></div>
    </div>
  );
}
