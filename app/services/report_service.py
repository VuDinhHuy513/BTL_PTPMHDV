"""Báo cáo quản trị. Xem R12.

TODO:

    occupancy(from, to)      → công suất từng ngày
    revenue(from, to, group_by)  → group_by ∈ {day, roomType, service}
    adr_revpar(from, to)     → ADR, RevPAR, occupancy tổng
    arrivals(date)           → khách đến trong ngày
    departures(date)         → khách đi trong ngày
    dashboard()              → số liệu tổng quan hôm nay

Công thức:
    Occupancy = đêm-phòng đã bán / đêm-phòng có thể bán × 100
    ADR       = doanh thu phòng / đêm-phòng đã bán
    RevPAR    = doanh thu phòng / đêm-phòng có thể bán

    "đêm-phòng có thể bán" = số phòng không bảo trì × số ngày trong kỳ

Doanh thu chỉ tính booking đã CheckedIn hoặc CheckedOut.
"""
