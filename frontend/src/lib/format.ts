export const money = (value: number | string | null | undefined) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value || 0))
export const number = (value: number | string | null | undefined) => new Intl.NumberFormat('vi-VN').format(Number(value || 0))
export const date = (value?: string | null) => value ? new Intl.DateTimeFormat('vi-VN').format(new Date(value)) : '—'
export const statusLabel: Record<string, string> = {
  LEAD: 'Khách hàng tiềm năng', QUALIFICATION: 'Đang xác minh nhu cầu', TECHNICAL_SURVEY: 'Khảo sát kỹ thuật', PROPOSAL: 'Đã báo giá', NEGOTIATION: 'Đàm phán', WON: 'Thắng', LOST: 'Thua',
  DRAFT: 'Nháp', CONFIRMED: 'Đã xác nhận', IMPLEMENTING: 'Đang triển khai', COMPLETED: 'Hoàn tất',
  PLANNING: 'Lập kế hoạch', IN_PROGRESS: 'Đang thực hiện', WAITING_ACCEPTANCE: 'Chờ nghiệm thu',
  PENDING: 'Chờ duyệt', APPROVED: 'Đã duyệt', REJECTED: 'Từ chối',
  OPEN: 'Đang mở', PARTIAL: 'Thanh toán một phần', PAID: 'Đã thanh toán', OVERDUE: 'Quá hạn',
  RESOLVED: 'Đã xử lý', CLOSED: 'Đã đóng', HIGH: 'Cao', MEDIUM: 'Trung bình', LOW: 'Thấp', CRITICAL: 'Khẩn cấp',
  // Lead
  NEW: 'Mới', CONTACTED: 'Đã liên hệ', QUALIFIED: 'Đủ điều kiện', CONVERTED: 'Đã chuyển đổi', DISQUALIFIED: 'Loại bỏ',
  // Quotation
  SUBMITTED: 'Đã gửi duyệt', REVIEWING: 'Đang xem xét', SENT_TO_CUSTOMER: 'Đã gửi khách hàng', EXPIRED: 'Hết hiệu lực',
  // Contract
  INTERNAL_REVIEW: 'Đang duyệt nội bộ', SENT_FOR_SIGNATURE: 'Chờ ký', SIGNED: 'Đã ký', ACTIVE: 'Đang hiệu lực', CANCELLED: 'Đã hủy',
  // Work order
  PLANNED: 'Đã lên kế hoạch', DONE: 'Hoàn thành',
  // Purchasing / stock reservation
  ORDERED: 'Đã đặt hàng', RECEIVED: 'Đã nhập kho', RESERVED: 'Đang giữ', FULFILLED: 'Đã xuất kho', RELEASED: 'Đã hủy giữ',
  // Tasks
  DONE_PENDING_REVIEW: 'Chờ xác nhận',
}
export const label = (value?: string | null) => value ? (statusLabel[value] || value.replaceAll('_', ' ')) : '—'
