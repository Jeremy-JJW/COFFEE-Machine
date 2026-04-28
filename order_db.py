import csv
import os
import threading
from datetime import datetime, timezone


class OrderDatabase:
    """
    咖啡订单数据库 (基于CSV文件)
    文件名: orders.csv
    格式: order_id, cups, created_time, status, completed_cups
    """

    _STANDARD_FIELDS = ['order_id', 'cups', 'created_time', 'status', 'completed_cups']

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(OrderDatabase, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.filename = "orders.csv"
        self.write_lock = threading.Lock()

        if not os.path.exists(self.filename):
            with self.write_lock:
                with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self._STANDARD_FIELDS)
        else:
            self._ensure_completed_cups_column()

    def _ensure_completed_cups_column(self):
        """旧表无 completed_cups 列时补齐，已有行默认 0。"""
        if not os.path.exists(self.filename):
            return
        with self.write_lock:
            with open(self.filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                if 'completed_cups' in fieldnames:
                    return
                rows = list(reader)
            fieldnames = fieldnames + ['completed_cups']
            temp_file = self.filename + '.tmp'
            with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    row['completed_cups'] = '0'
                    writer.writerow(row)
            os.replace(temp_file, self.filename)
            print(" 已升级 orders.csv：增加 completed_cups 列")

    def add_order(self, order_id, cups):
        """添加新订单，status=0，completed_cups=0"""
        self._ensure_completed_cups_column()
        created_time = datetime.now().replace(microsecond=0).astimezone(timezone.utc).isoformat()

        with self.write_lock:
            rows = []
            fieldnames = list(self._STANDARD_FIELDS)
            if os.path.exists(self.filename):
                with open(self.filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = list(reader.fieldnames or fieldnames)
                    if 'completed_cups' not in fieldnames:
                        fieldnames.append('completed_cups')
                    rows = list(reader)

            new_row = {fn: '' for fn in fieldnames}
            new_row['order_id'] = str(order_id)
            new_row['cups'] = str(cups)
            new_row['created_time'] = created_time
            new_row['status'] = '0'
            new_row['completed_cups'] = '0'

            rows.append(new_row)

            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        print(f" 订单 {order_id} (共 {cups} 杯) 已存入数据库")

    def get_pending_orders(self):
        """获取所有待处理的订单列表（status=0）"""
        pending_orders = []
        if not os.path.exists(self.filename):
            return pending_orders

        with self.write_lock:
            with open(self.filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('status') == '0':
                        order = {
                            'order_id': int(row['order_id']),
                            'cups': int(row['cups']),
                            'created_time': row['created_time'],
                        }
                        if row.get('completed_cups') not in (None, ''):
                            order['completed_cups'] = int(row['completed_cups'])
                        else:
                            order['completed_cups'] = 0
                        pending_orders.append(order)
        return pending_orders

    def get_next_pending_order(self):
        pending_orders = self.get_pending_orders()
        if not pending_orders:
            return None
        pending_orders.sort(key=lambda x: x['created_time'])
        return pending_orders[0]

    def mark_order_as_processing(self, order_id):
        return self._update_order_status(order_id, 1)

    def mark_order_as_completed(self, order_id):
        return self._update_order_status(order_id, 2)

    def increment_completed_cups(self, order_id):
        """
        每完成一杯物理制作，将对应订单行的 completed_cups +1。
        只更新第一条匹配的、且 status 为 0 或 1 的订单行。
        """
        if not os.path.exists(self.filename):
            return False

        self._ensure_completed_cups_column()
        temp_file = self.filename + '.tmp'
        updated = False

        with self.write_lock:
            with open(self.filename, 'r', newline='', encoding='utf-8') as infile, \
                    open(temp_file, 'w', newline='', encoding='utf-8') as outfile:

                reader = csv.DictReader(infile)
                fieldnames = list(reader.fieldnames or [])
                if 'completed_cups' not in fieldnames:
                    fieldnames.append('completed_cups')
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    if row.get('completed_cups') in (None, ''):
                        row['completed_cups'] = '0'
                    oid = int(row.get('order_id', -1))
                    st = row.get('status', '')
                    if (
                        not updated
                        and oid == order_id
                        and st in ('0', '1')
                    ):
                        old = int(row['completed_cups'])
                        row['completed_cups'] = str(old + 1)
                        updated = True
                    writer.writerow(row)

            if updated:
                os.replace(temp_file, self.filename)
                print(f" 订单 {order_id} 已完成杯数 +1（CSV completed_cups 已更新）")
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        return updated

    def _update_order_status(self, order_id, new_status):
        if not os.path.exists(self.filename):
            return False

        self._ensure_completed_cups_column()
        updated = False
        temp_file = self.filename + '.tmp'

        with self.write_lock:
            with open(self.filename, 'r', newline='', encoding='utf-8') as infile, \
                    open(temp_file, 'w', newline='', encoding='utf-8') as outfile:

                reader = csv.DictReader(infile)
                fieldnames = list(reader.fieldnames or [])
                if 'completed_cups' not in fieldnames:
                    fieldnames.append('completed_cups')
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    if row.get('completed_cups') in (None, ''):
                        row['completed_cups'] = '0'
                    if int(row.get('order_id', -1)) == order_id:
                        row['status'] = str(new_status)
                        if new_status == 2:
                            row['completed_cups'] = str(row.get('cups', row['completed_cups']))
                        updated = True
                    writer.writerow(row)

            if updated:
                os.replace(temp_file, self.filename)
                print(f" 订单 {order_id} 状态更新为: {self._get_status_name(new_status)}")
            elif os.path.exists(temp_file):
                os.remove(temp_file)

        return updated

    def _get_status_name(self, status_code):
        status_names = {
            0: "未处理",
            1: "处理中",
            2: "已完成",
        }
        return status_names.get(status_code, f"未知状态({status_code})")

    def count_pending_cups(self):
        """
        首页「待制作杯数」：所有未完结订单（status 为 0 或 1）的剩余杯数之和。
        剩余 = max(0, cups - completed_cups)，做单过程中会随 completed_cups 增加而减少。
        """
        if not os.path.exists(self.filename):
            return 0
        self._ensure_completed_cups_column()
        total = 0
        with self.write_lock:
            with open(self.filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('status') not in ('0', '1'):
                        continue
                    try:
                        cups = int(row['cups'])
                    except (KeyError, ValueError):
                        continue
                    raw = row.get('completed_cups')
                    try:
                        done = int(raw) if raw not in (None, '') else 0
                    except ValueError:
                        done = 0
                    total += max(0, cups - done)
        return total


order_db = OrderDatabase()
