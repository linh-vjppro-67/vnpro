# Security checklist trước go-live

- Thay `SECRET_KEY` và toàn bộ mật khẩu mặc định.
- Bật HTTPS/TLS tại load balancer hoặc Nginx.
- Hạn chế `CORS_ORIGINS` về domain thật.
- Dùng PostgreSQL riêng, tài khoản DB quyền tối thiểu.
- Bật backup tự động và diễn tập restore.
- Bổ sung MFA/SSO cho Ban giám đốc, Kế toán và quản trị.
- Lưu hồ sơ/attachment trên object storage có mã hóa và lifecycle.
- Cấu hình rate limit, WAF, cảnh báo đăng nhập bất thường.
- Đẩy log đến hệ thống tập trung; không ghi secret hoặc dữ liệu nhạy cảm vào log.
- Penetration test, kiểm thử phân quyền ngang/dọc trước UAT.
- Rà soát Nghị định 13/2023/NĐ-CP cho dữ liệu cá nhân nhân sự/khách hàng.
