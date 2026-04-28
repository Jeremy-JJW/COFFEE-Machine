from flask import Flask, request, redirect, url_for, render_template, jsonify
from threading import Lock
import datetime
import socket
from order_db import order_db  # 导入订单数据库

# app = Flask(__name__)
app = Flask(__name__, static_folder='static')

# 全局变量保存订单信息（线程安全）
next_order_id = 1  # 新增：订单ID计数器
order_lock = Lock() 
last_order_time = None
order_history = []

 
# 获取本机IP地址和当前时间（保持不变）
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # return datetime.datetime.now()


# 主页 - 展示订单表单 00000
@app.route('/')
def order_page():
    # 处理可能的错误消息
    error_message = request.args.get('error', '')

    # 获取本机IP地址
    ip_address = get_local_ip()

    # 获取当前时间
    current_time = get_current_time()

    # 从数据库中获取待处理订单总杯数
    pending_cups = order_db.count_pending_cups()

    return render_template(
        'index.html',
        ip_address=ip_address,
        current_time=current_time,
        error=error_message,
        pending_cups=pending_cups
    )


@app.route('/api/order_status')
def api_order_status():
    """首页轮询：返回待制作总杯数（与 CSV 中 status=0 的订单一致）"""
    pending_cups = order_db.count_pending_cups()
    return jsonify(success=True, pending_cups=pending_cups)
 

# 下单处理 网页上点击下单后提交表单首先在这里处理  11111
@app.route('/order', methods=['POST'])
def place_order():
    global next_order_id, last_order_time, order_history

    # 获取杯子数量
    cups = request.form.get('cups')
    try:
        cups = int(cups)
        if cups < 1 or cups > 10:
            raise ValueError("杯数超出范围")
    except:
        # 重定向回主页并显示错误消息
        return redirect(url_for('order_page', error="请输入有效的杯数（1-10）"))

    # 加锁处理全局变量
    with order_lock:
        # 生成订单信息
        order_id = next_order_id
        next_order_id += 1
        now = datetime.datetime.now()
        last_order_time = now

        # 记录订单到内存历史中
        order_history.append({
            "id": order_id,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "cups": cups
        })

        # 将订单提交到数据库。
        order_db.add_order(order_id, cups)

    print(f"订单 #{order_id}：{cups}杯咖啡 (已提交到数据库)")

    # 跳转到成功页面
    return redirect(url_for('order_success', cups=cups))


# 订单成功页面  22222
@app.route('/order/success')
def order_success():
    cups = request.args.get('cups', '0')
    current_time = get_current_time()
    return render_template('success.html', cups=cups, current_time=current_time)


# 订单明细页面
@app.route('/orders')
def order_details():
    # 计算已完成的总杯数
    total_cups = sum(order['cups'] for order in order_history)

    # 从数据库获取最新状态信息
    pending_orders = order_db.get_pending_orders()
    pending_cups = order_db.count_pending_cups()
    completed_orders_count = len(order_history) - len(pending_orders)

    return render_template(
        'orders.html',
        total_cups=total_cups,
        pending_cups=pending_cups,
        order_count=len(order_history),
        completed_orders_count=completed_orders_count,
        orders=order_history,
        pending_orders=pending_orders,
        current_time=get_current_time()
    )


if __name__ == '__main__':
    # 获取本机在局域网中的IP
    ip = get_local_ip()
    print(f" * 本地访问: http://127.0.0.1:5000")
    print(f" * 其他设备访问: http://{ip}:5000")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )









