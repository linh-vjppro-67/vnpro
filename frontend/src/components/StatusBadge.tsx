import { label } from '../lib/format'
export function StatusBadge({ value }: {value?: string | null}) {
  const safe = value || 'UNKNOWN'
  return <span className={`badge badge-${safe.toLowerCase()}`}>{label(safe)}</span>
}
