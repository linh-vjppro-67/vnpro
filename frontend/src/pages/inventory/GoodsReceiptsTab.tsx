import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { api } from '../../lib/api'
import { date } from '../../lib/format'
import { DataTable } from '../../components/DataTable'
import { StatusBadge } from '../../components/StatusBadge'

type ReceiptLine = {
  product_id: number
  received_quantity: number
  accepted_quantity: number
  quarantine_quantity: number
  rejected_quantity: number
  quality_note: string
}

export function GoodsReceiptsTab({ products, onChange }: { products: any[]; onChange?: () => void }) {
  const [rows, setRows] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [show, setShow] = useState(false)
  const [selectedPo, setSelectedPo] = useState<any>()
  const [lines, setLines] = useState<ReceiptLine[]>([])
  const [error, setError] = useState('')
  const load = () => Promise.all([api.get('/production/goods-receipts'), api.get('/purchasing/orders')])
    .then(([receipts, pos]) => { setRows(receipts.data); setOrders(pos.data.filter((x: any) => ['ORDERED','PARTIALLY_RECEIVED'].includes(x.status))) })
  useEffect(() => { load() }, [])

  const selectPo = (id: number) => {
    const po = orders.find(x => x.id === id)
    setSelectedPo(po)
    setLines((po?.items || []).map((x: any) => ({
      product_id: x.product_id, received_quantity: x.quantity, accepted_quantity: x.quantity,
      quarantine_quantity: 0, rejected_quantity: 0, quality_note: '',
    })))
  }
  const patchLine = (index: number, patch: Partial<ReceiptLine>) =>
    setLines(lines.map((line, i) => i === index ? { ...line, ...patch } : line))
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setError('')
    const f = new FormData(e.currentTarget)
    try {
      await api.post('/production/goods-receipts', {
        code: f.get('code'), purchase_order_id: selectedPo.id, received_date: f.get('received_date'),
        delivery_note: f.get('delivery_note') || null,
        document_checklist: { purchase_order: !!f.get('doc_po'), delivery_note: !!f.get('doc_delivery'), quality_record: !!f.get('doc_quality') },
        lines,
      })
      setShow(false); setSelectedPo(undefined); setLines([]); await load()
    } catch (err: any) { setError(err?.response?.data?.detail || 'Không thể tạo phiếu nhập') }
  }
  const post = async (id: number) => {
    try { await api.post(`/production/goods-receipts/${id}/post`); await load(); onChange?.() }
    catch (err: any) { setError(err?.response?.data?.detail || 'Không thể ghi sổ phiếu nhập') }
  }
  const productName = (id: number) => products.find(p => p.id === id)?.name || `#${id}`

  return <>
    <div className="toolbar"><span>{rows.length} phiếu kiểm nhận</span><button className="primary-btn small" onClick={() => setShow(true)}><Plus size={15}/> Kiểm nhận hàng</button></div>
    {error && <div className="error-panel">{error}</div>}
    <div className="panel"><DataTable rows={rows} columns={[
      { key: 'code', label: 'Mã phiếu' },
      { key: 'purchase_order_id', label: 'PO', render: (r: any) => orders.find(x => x.id === r.purchase_order_id)?.code || `PO #${r.purchase_order_id}` },
      { key: 'received_date', label: 'Ngày nhận', render: (r: any) => date(r.received_date) },
      { key: 'lines', label: 'Kết quả', render: (r: any) => `${r.lines.reduce((s: number, x: any) => s + x.accepted_quantity, 0)} đạt · ${r.lines.reduce((s: number, x: any) => s + x.quarantine_quantity, 0)} cách ly` },
      { key: 'status', label: 'Trạng thái', render: (r: any) => <StatusBadge value={r.status}/> },
      { key: 'actions', label: '', render: (r: any) => r.status === 'INSPECTED' && <button className="table-btn" onClick={() => post(r.id)}>Post nhập kho</button> },
    ]}/></div>
    {show && <div className="modal-backdrop" onMouseDown={() => setShow(false)}><form className="modal" onSubmit={submit} onMouseDown={e => e.stopPropagation()}>
      <h3>Kiểm nhận hàng theo PO</h3>
      {error && <div className="error-panel">{error}</div>}
      <div className="form-grid">
        <label>Mã phiếu nhập<input name="code" required placeholder="GR-2026-001"/></label>
        <label>Đơn mua hàng<select required defaultValue="" onChange={e => selectPo(Number(e.target.value))}><option value="" disabled>Chọn PO đã đặt</option>{orders.map(x => <option key={x.id} value={x.id}>{x.code}</option>)}</select></label>
        <label>Ngày nhận<input name="received_date" type="date" required defaultValue={new Date().toISOString().slice(0, 10)}/></label>
        <label>Số phiếu giao<input name="delivery_note"/></label>
      </div>
      <div className="check-list">
        <label><input name="doc_po" type="checkbox" required/> PO/hợp đồng mua</label>
        <label><input name="doc_delivery" type="checkbox" required/> Phiếu giao hàng</label>
        <label><input name="doc_quality" type="checkbox" required/> Biên bản kiểm tra</label>
      </div>
      {lines.map((line, i) => <div className="form-grid" key={line.product_id}>
        <label className="full">{productName(line.product_id)}</label>
        <label>SL nhận<input type="number" min="1" value={line.received_quantity} onChange={e => patchLine(i, { received_quantity: Number(e.target.value) })}/></label>
        <label>Đạt<input type="number" min="0" value={line.accepted_quantity} onChange={e => patchLine(i, { accepted_quantity: Number(e.target.value) })}/></label>
        <label>Cách ly<input type="number" min="0" value={line.quarantine_quantity} onChange={e => patchLine(i, { quarantine_quantity: Number(e.target.value) })}/></label>
        <label>Từ chối<input type="number" min="0" value={line.rejected_quantity} onChange={e => patchLine(i, { rejected_quantity: Number(e.target.value) })}/></label>
        <label className="full">Kết quả kiểm tra<input value={line.quality_note} onChange={e => patchLine(i, { quality_note: e.target.value })}/></label>
      </div>)}
      <div className="modal-actions"><button type="button" className="ghost-btn" onClick={() => setShow(false)}>Hủy</button><button className="primary-btn" disabled={!selectedPo}>Lưu biên bản kiểm nhận</button></div>
    </form></div>}
  </>
}
