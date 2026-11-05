"""Project workbook export.

The desktop app embedded a Pillow PNG. Pillow is not available in Python
Workers, so the gantt sheet is drawn with cell fills instead.
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta, timezone

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

STATUS_LABELS = {
    "todo": "未开始",
    "progress": "进行中",
    "delayed": "延期",
    "done": "已完成",
    "cancelled": "已取消",
}
PRIORITY_LABELS = {"low": "低", "normal": "中", "high": "高", "urgent": "紧急"}
STATUS_COLORS = {
    "todo": "8E8E93",
    "progress": "0071E3",
    "delayed": "FF9500",
    "done": "34C759",
    "cancelled": "AF52DE",
}

THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
HEADER_FILL = PatternFill("solid", fgColor="23282D")
HEADER_FONT = Font(name="Microsoft YaHei", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="Microsoft YaHei", size=10)


def _as_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def export_project_workbook(project: dict, tasks: list[dict], costs: list[dict]) -> bytes:
    workbook = Workbook()
    _write_overview(workbook, project, tasks, costs)
    _write_tasks(workbook, tasks)
    _write_costs(workbook, costs, tasks)
    _write_gantt(workbook, tasks)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _write_overview(workbook: Workbook, project: dict, tasks: list[dict], costs: list[dict]) -> None:
    sheet = workbook.active
    sheet.title = "项目概览"
    sheet.column_dimensions["A"].width = 16
    sheet.column_dimensions["B"].width = 70
    total = sum(float(cost["amount"]) for cost in costs)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    this_month = sum(float(cost["amount"]) for cost in costs if str(cost["spent_at"]).startswith(month))
    done = sum(1 for task in tasks if task["status"] == "done")
    delayed = sum(1 for task in tasks if task["status"] == "delayed")
    average = sum(int(task["progress"] or 0) for task in tasks) / len(tasks) if tasks else 0
    rows = [
        ("名称", project["name"]),
        ("颜色", project["color"]),
        ("状态", project["status"]),
        ("开始日期", project["start_date"] or ""),
        ("结束日期", project["end_date"] or ""),
        ("描述", project["description"] or ""),
        ("", ""),
        ("任务总数", len(tasks)),
        ("已完成", done),
        ("延期", delayed),
        ("平均进度", f"{average:.0f}%"),
        ("本月支出", f"¥{this_month:.2f}"),
        ("总支出", f"¥{total:.2f}"),
        ("", ""),
        ("导出时间", datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
    ]
    for index, (label, value) in enumerate(rows, start=1):
        key_cell = sheet.cell(index, 1, label)
        value_cell = sheet.cell(index, 2, value)
        if label:
            key_cell.font = Font(name="Microsoft YaHei", size=10, bold=True)
            key_cell.fill = PatternFill("solid", fgColor="F2F2F5")
        value_cell.font = BODY_FONT
        value_cell.alignment = Alignment(vertical="top", wrap_text=True)


def _write_tasks(workbook: Workbook, tasks: list[dict]) -> None:
    sheet = workbook.create_sheet("任务清单")
    headers = ["ID", "名称", "父任务", "状态", "优先级", "开始", "结束", "持续(天)", "进度", "里程碑", "描述"]
    widths = [8, 30, 18, 10, 8, 12, 12, 10, 8, 8, 40]
    for column, (header, width) in enumerate(zip(headers, widths), start=1):
        cell = sheet.cell(1, column, header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.freeze_panes = "A2"
    by_id = {task["id"]: task for task in tasks}
    ordered = sorted(tasks, key=lambda task: (task["parent_id"] or 0, task["sort_order"], task["id"]))
    for row_index, task in enumerate(ordered, start=2):
        parent = by_id.get(task["parent_id"])
        start = _as_date(task["start_date"])
        end = _as_date(task["end_date"])
        duration = (end - start).days + 1 if start and end else ""
        values = [
            task["id"],
            task["name"],
            parent["name"] if parent else "",
            STATUS_LABELS.get(task["status"], task["status"]),
            PRIORITY_LABELS.get(task["priority"], task["priority"]),
            task["start_date"] or "",
            task["end_date"] or "",
            duration,
            f"{task['progress']}%",
            "是" if task["is_milestone"] else "",
            task["description"] or "",
        ]
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_index, column, value)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=(column == 11))


def _write_costs(workbook: Workbook, costs: list[dict], tasks: list[dict]) -> None:
    sheet = workbook.create_sheet("费用记录")
    headers = ["ID", "名称", "类别", "金额", "日期", "关联任务", "描述"]
    widths = [8, 28, 12, 12, 12, 18, 36]
    for column, (header, width) in enumerate(zip(headers, widths), start=1):
        cell = sheet.cell(1, column, header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.freeze_panes = "A2"
    names = {task["id"]: task["name"] for task in tasks}
    ordered = sorted(costs, key=lambda cost: (str(cost["spent_at"]), cost["id"]))
    for row_index, cost in enumerate(ordered, start=2):
        task_label = names.get(cost["task_id"], "")
        if cost["task_id"] and not task_label:
            task_label = f"#{cost['task_id']}"
        values = [
            cost["id"],
            cost["name"],
            cost["category"],
            float(cost["amount"]),
            cost["spent_at"],
            task_label,
            cost["description"] or "",
        ]
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_index, column, value)
            cell.font = BODY_FONT
            cell.border = BORDER
            if column == 4:
                cell.number_format = "¥#,##0.00"


def _write_gantt(workbook: Workbook, tasks: list[dict]) -> None:
    sheet = workbook.create_sheet("甘特图")
    dated = []
    for task in tasks:
        start = _as_date(task.get("start_date"))
        if start is None:
            continue
        end = _as_date(task.get("end_date")) or start
        dated.append((task, start, end))
    dated.sort(key=lambda item: (item[1], item[0]["id"]))
    if not dated:
        sheet["A1"] = "暂无带日期的任务"
        return
    min_day = min(item[1] for item in dated)
    max_day = max(item[2] for item in dated)
    span = (max_day - min_day).days + 1
    step = 7 if span > 90 else 1
    columns = []
    cursor = min_day
    while cursor <= max_day:
        columns.append(cursor)
        cursor += timedelta(days=step)
    sheet.cell(1, 1, "任务").font = HEADER_FONT
    sheet.cell(1, 1).fill = HEADER_FILL
    sheet.column_dimensions["A"].width = 28
    for index, day in enumerate(columns, start=2):
        cell = sheet.cell(1, index, day.strftime("%m-%d"))
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", textRotation=90)
        sheet.column_dimensions[get_column_letter(index)].width = 4
    for row_index, (task, start, end) in enumerate(dated, start=2):
        sheet.cell(row_index, 1, task["name"]).font = BODY_FONT
        color = STATUS_COLORS.get(task["status"], "8E8E93")
        fill = PatternFill("solid", fgColor=color)
        for index, day in enumerate(columns, start=2):
            window_end = day + timedelta(days=step - 1)
            if start <= window_end and end >= day:
                sheet.cell(row_index, index).fill = fill
    sheet.freeze_panes = "B2"
    note = f"时间范围 {min_day.isoformat()} → {max_day.isoformat()}"
    if step > 1:
        note += "（按周着色）"
    sheet.cell(len(dated) + 3, 1, note).font = BODY_FONT
