import type { ReactNode } from 'react'
export type Column<T> = { key: string; label: string; render?: (row: T) => ReactNode; className?: string }
export function DataTable<T extends Record<string, unknown>>({ rows, columns, empty = 'Chưa có dữ liệu' }: {rows: T[]; columns: Column<T>[]; empty?: string}) {
  return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>
    {rows.length === 0 ? <tr><td colSpan={columns.length} className="empty">{empty}</td></tr> : rows.map((row, i) => <tr key={(row.id as number|string) ?? i}>{columns.map(c => <td key={c.key} className={c.className}>{c.render ? c.render(row) : String(row[c.key] ?? '—')}</td>)}</tr>)}
  </tbody></table></div>
}
