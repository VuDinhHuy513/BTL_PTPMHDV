"""TODO — AuditLog: nhật ký ai làm gì lúc nào.

    id, user_id (FK nullable), entity (index), entity_id (index)
    action, detail: Text, created_at (index)

Ghi log cho các thao tác nhạy cảm: sửa booking, hủy, giảm giá, check-in/out.
"""
