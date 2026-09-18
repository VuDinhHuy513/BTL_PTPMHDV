"""Đăng nhập, cấp token, quản lý tài khoản.

TODO:

    login(dto) -> TokenOut
        Tìm user theo username, verify_password.
        ⚠ Sai username và sai mật khẩu phải trả CÙNG một thông báo lỗi —
          nếu phân biệt, kẻ tấn công dò được username nào tồn tại.
        Kiểm tra is_active.
        Trả access_token + refresh_token (hàm đã có ở app/core/security.py).

    refresh(refresh_token) -> TokenOut
    create_user(dto)      ← hash_password, không lưu mật khẩu thô
    update_user(user_id, dto)
    set_active(user_id, is_active)
"""
