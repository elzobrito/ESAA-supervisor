interface ArtifactTypeFilterProps {
  label: string;
  value: string;
  options: string[];
  allLabel: string;
  onChange: (value: string) => void;
}

export function ArtifactTypeFilter({
  label,
  value,
  options,
  allLabel,
  onChange,
}: ArtifactTypeFilterProps) {
  return (
    <label className="artifact-filter">
      <span className="artifact-filter-label">{label}</span>
      <select className="filter-select-ds" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="all">{allLabel}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
