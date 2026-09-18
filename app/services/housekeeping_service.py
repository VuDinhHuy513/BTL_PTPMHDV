"""Buồng phòng.

TODO:
    list_tasks(date, status, assignee_id)
    create_task(dto)
    update_task(task_id, dto)
        Khi status → DONE: ghi completed_at, và nếu phòng đang Dirty
        thì chuyển sang Inspected.
    room_status_board()
        Bảng trạng thái toàn bộ phòng kèm tên khách đang ở.
"""
