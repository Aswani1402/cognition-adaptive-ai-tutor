interface CodeEditorBoxProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  minHeight?: number;
}

export default function CodeEditorBox({ value, onChange, disabled, minHeight = 220 }: CodeEditorBoxProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="w-full min-w-0 flex-1 resize-y bg-[#0d1117] text-slate-200 font-mono text-sm p-4 focus:outline-none"
      style={{ minHeight }}
      spellCheck={false}
      aria-label="Code editor"
    />
  );
}
