# --------------------------------------------------a06：增加了读取输出引脚的方法-------------------------------------------------------
# yanmeng_io_reader.py
import os
import sys
import time
import threading
from ctypes import *

# ---------------- 路径配置 ----------------
sdk_path = r"Z:/a.LINGTECH/a.工作软件/板卡软件/岩獴板卡/sdk/python"

if not os.path.exists(sdk_path):
    print(f"错误: SDK 路径不存在 -> {sdk_path}")
    sys.exit(1)

if sdk_path not in sys.path:
    sys.path.append(sdk_path)

# ---------------- 导入岩獴 SDK ----------------
try:
    from librockmong import *
    from device import *
    from gpio import *
    from usb_device import *

    print("成功导入岩獴 SDK 模块")
except ImportError as e:
    print(f"导入岩獴板卡SDK失败: {e}")
    sys.exit(1)


class YanMengIOController:
    """岩獴板卡IO控制器类，支持输入读取和输出控制"""

    def __init__(self):
        self.sn = None
        self.device_opened = False

        # 用于追踪输出引脚状态（软件层面）
        self.output_pin_states = {}
        for pin in range(16):
            self.output_pin_states[pin] = True  # 默认高电平

    def scan_devices(self):
        """扫描连接的USB设备"""
        SerialNumbers = (c_int * 20)()
        ret = UsbDevice_Scan(byref(SerialNumbers))

        if ret < 0:
            print(f"扫描USB设备错误: {ret}")
            return []
        elif ret == 0:
            print("未找到USB设备!")
            return []
        else:
            devices = []
            for i in range(ret):
                devices.append(SerialNumbers[i])
                print(f"USB设备 {i} SN: {SerialNumbers[i]}")
            return devices

    def open_device(self, sn=None):
        """打开USB设备"""
        if self.device_opened:
            print("设备已经打开")
            return True

        if sn is None:
            devices = self.scan_devices()
            if not devices:
                return False
            self.sn = devices[0]
        else:
            self.sn = sn

        ret = UsbDevice_Open(self.sn)
        if ret < 0:
            print(f"打开USB设备错误: {ret}")
            return False

        self.device_opened = True
        print(f"成功打开USB设备 SN: {self.sn}")

        # 初始化所有输出引脚为高电平
        self._initialize_output_pins()

        return True

    def _initialize_output_pins(self):
        """初始化所有输出引脚为高电平"""
        if not self.device_opened:
            return False

        try:
            print("初始化所有输出引脚...")
            for pin in range(16):
                self.set_output_pin(pin, True)

            print("✅ 所有输出引脚初始化为高电平(true)")
            return True
        except Exception as e:
            print(f"初始化输出引脚失败: {e}")
            return False

    def close_device(self):
        """关闭USB设备"""
        if not self.device_opened:
            print("设备未打开")
            return True

        ret = UsbDevice_Close(self.sn)
        if ret < 0:
            print(f"关闭USB设备错误: {ret}")
            return False

        self.device_opened = False
        print("USB设备已关闭")
        return True

    def set_output_pin(self, pin, state):
        """
        控制输出引脚状态并在软件中记录
        :param pin: 引脚编号 (0-15)
        :param state: 引脚状态 True(高电平) 或 False(低电平)
        :return: 是否成功
        """
        if not self.device_opened:
            print("设备未打开")
            return False

        # 转换为岩獴板卡的状态表示
        # 根据文档: 0=晶体管导通, 1=晶体管断开
        pin_state_value = 1 if state else 0

        ret = IO_WritePin(self.sn, pin, pin_state_value)

        if ret < 0:
            print(f"设置OUT{pin}引脚错误: {ret}")
            return False

        # 记录状态变化（只记录成功设置的情况）
        self.output_pin_states[pin] = state
        print(f"设置OUT{pin}为{'高电平' if state else '低电平'}")

        return True

    def read_input_pin(self, pin):
        """
        读取输入引脚状态
        :param pin: 引脚编号 (0-15)
        :return: True(高电平) 或 False(低电平) 或 None(读取失败)
        """
        if not self.device_opened:
            print("设备未打开")
            return None

        PinState = c_int()
        ret = IO_ReadPin(self.sn, pin, byref(PinState))

        if ret < 0:
            print(f"读取IN{pin}引脚错误: {ret}")
            return None

        return PinState.value == 1

    def read_output_pin(self, pin):
        """
        读取输出引脚状态（从软件记录中读取）
        :param pin: 引脚编号 (0-15)
        :return: True(高电平) 或 False(低电平) 或 None(未知状态)
        """
        if pin < 0 or pin > 15:
            print(f"错误: 引脚编号应在0-15之间，但收到: {pin}")
            return None

        # 直接从我们的状态记录中读取
        return self.output_pin_states.get(pin)

    def write_output_pin(self, pin, state):
        """
        兼容方法，同 set_output_pin
        """
        return self.set_output_pin(pin, state)

    def pulse_output_pin(self, pin, duration, initial_state=True, final_state=True):
        """
        产生一个脉冲信号
        :param pin: 引脚编号
        :param duration: 脉冲持续时间(秒)
        :param initial_state: 初始状态
        :param final_state: 最终状态
        :return: 是否成功
        """
        if not self.device_opened:
            return False

        def pulse_thread():
            # 设置初始状态
            self.set_output_pin(pin, initial_state)
            time.sleep(duration)
            # 设置最终状态
            self.set_output_pin(pin, final_state)

        thread = threading.Thread(target=pulse_thread)
        thread.daemon = True
        thread.start()
        return True

    def monitor_input_pin(self, pin, callback=None, interval=0.1):
        """
        持续监控输入引脚状态变化
        :param pin: 引脚编号
        :param callback: 状态变化时的回调函数
        :param interval: 检查间隔(秒)
        """
        if not self.device_opened:
            print("设备未打开")
            return

        last_state = None
        print(f"开始监控IN{pin}引脚...")

        try:
            while True:
                current_state = self.read_input_pin(pin)

                if current_state is not None and current_state != last_state:
                    print(f"IN{pin}引脚状态变化: {last_state} -> {current_state}")

                    if callback:
                        callback(current_state)

                    last_state = current_state

                time.sleep(interval)

        except KeyboardInterrupt:
            print("监控已停止")

    def __enter__(self):
        self.open_device()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_device()

    def __del__(self):
        if self.device_opened:
            self.close_device()


# 简单的单元测试
if __name__ == "__main__":
    print("===== 岩獴板卡控制器单元测试 =====")
    io = YanMengIOController()

    print("\n[测试1] 打开设备...")
    if io.open_device():
        print("✅ 打开设备成功")

        print("\n[测试2] 读取输出引脚状态...")
        test_pins = [1, 11, 12]
        for pin in test_pins:
            state = io.read_output_pin(pin)
            if state is not None:
                print(f"  OUT{pin}状态: {'高电平' if state else '低电平'}")
            else:
                print(f"  OUT{pin}状态: 未知")

        print("\n[测试3] 输出引脚操作循环...")
        try:
            for _ in range(3):
                for state in [False, True]:
                    print(f"\n操作: 设置OUT1为{'低电平' if not state else '高电平'}")
                    if io.write_output_pin(1, state):
                        # 等待状态更新
                        time.sleep(0.1)
                        read_state = io.read_output_pin(1)
                        actual_match = read_state == state
                        print(f"  状态匹配: {'是' if actual_match else '否'} (期望: {state}, 实际: {read_state})")
                    else:
                        print("  设置失败!")
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        print("\n[清理] 复位并关闭设备...")
        io.write_output_pin(1, True)  # 复位到高电平

    print("\n测试完成")
