# Subject Card Visual Fix Report

## 1. Root Cause
- Subject cards depended directly on `subject.icon` and `subject.color` values from API/mock data.
- If backend subject data omitted, renamed, or returned an unexpected icon/color for Python or SQL / Database, the icon box and action button could render as blank or white-on-white.
- Tailwind dynamic class use was also fragile because backend-provided class names are not guaranteed to be present in the compiled CSS.

## 2. Files Patched
- `src/components/learning/SubjectCard.tsx`

## 3. Icons Used Per Subject
- Python: `Code2`, blue `bg-sky-600`
- SQL / Database: `Database`, indigo `bg-indigo-600`
- HTML/Web Basics: `Globe`, orange `bg-orange-500`
- Git: `GitBranch`, pink `bg-pink-600`
- Data Structures: `Network`, green `bg-emerald-600`

## 4. Button Visibility Status
- `Start Guided Session` is always visible for every subject card.
- Button text is white on a colored background.
- Button uses the same resolved subject color as the icon, with hover contrast preserved.
- Card click handler remains unchanged through `onSelect(subject)`.

## 5. Build/Lint Result
- `npm run build`: passed
- `npm run lint`: passed
