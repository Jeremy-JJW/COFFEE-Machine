# ----------------------------------------------------------------------------------------------------------------------------------------------

# ----------------------------coffee_simple的程序就是这个，所以只看这个文件就好了，单次调用，只制作美式  （暂时为用到的版本）------------------------------------------------------------
import serial
import time
import logging

class CoffeeMachineController:
    def __init__(self, port: str, baudrate: int = 38400, timeout: int = 5):
        """
        初始化咖啡机控制器
        :param port: 串口端口，例如 'COM7' (Windows) 或 '/dev/ttyUSB0' (Linux)
        :param baudrate: 波特率，根据文档设置为38400
        :param timeout: 超时时间，默认5秒
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        # 配置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """连接到咖啡机"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.logger.info(f"成功连接到咖啡机，端口: {self.port}, 波特率: {self.baudrate}")
            return True
        except serial.SerialException as e:
            self.logger.error(f"连接咖啡机失败: {e}")
            return False

    def disconnect(self):
        """断开与咖啡机的连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("已断开与咖啡机的连接")

    def cal_lrc_common(self, data):
        """
        计算LRC校验码
        :param data: 需要计算校验码的数据字符串（十六进制格式）
        :return: 两位十六进制校验码字符串
        """
        try:
            if len(data) % 2 != 0:
                data = data + "0"

            total = 0
            num = 0
            length = len(data)

            while num < length:
                s = data[num:num + 2]
                total += int(s, 16)
                num += 2

            total = (~total + 1) & 0xFF  # 限制在8位范围内
            checksum = hex(total)[2:].upper()

            if len(checksum) < 2:
                checksum = checksum.zfill(2)

            return checksum
        except Exception as e:
            self.logger.error(f"计算LRC校验码时出错: {e}")
            return "00"

    def send_command(self, command: str, data: str) -> str:
        """
        向咖啡机发送命令并接收响应
        :param command: 命令代码（两位十六进制）
        :param data: 命令数据（十六进制字符串）
        :return: 响应数据
        """
        if not self.ser or not self.ser.is_open:
            self.logger.error("未连接到咖啡机")
            return ""

        try:
            # 构建完整数据帧（不包括帧起始符和结束校验码LRC）
            frame_data = f"01{command}{data}"

            # 计算校验码
            lrc = self.cal_lrc_common(frame_data)

            # 构建完整命令（保持\r\n作为字面字符串）
            full_command = f":{frame_data}{lrc}\\r\\n"
            command_bytes = full_command.encode('ascii')

            self.logger.info(f"发送命令: {full_command}")

            # 清空输入缓冲区
            self.ser.reset_input_buffer()

            # 发送命令
            self.ser.write(command_bytes)
            self.ser.flush()  # 确保数据发送完成

            # 等待并读取响应
            time.sleep(0.5)  # 等待咖啡机响应
            response = self.ser.read_all()

            if response:
                response_str = response.decode('ascii', errors='ignore')
                self.logger.info(f"收到响应: {response_str}")
                self.logger.info(f"响应十六进制: {' '.join([f'{b:02X}' for b in response])}")
                return response_str
            else:
                self.logger.warning("未收到响应")
                return ""

        except Exception as e:
            self.logger.error(f"发送命令时出错: {e}")
            return ""

    def make_americano(self) -> bool:
        """
        发送制作美式咖啡的指令
        :return: 是否成功发送指令
        """
        # 美式咖啡的控制内容为0002（根据文档第5页）
        response = self.send_command("01", "0002")

        # 只要收到响应就认为是成功发送
        if response:
            self.logger.info("咖啡制作指令已发送，等待咖啡机响应...")
            return True
        else:
            self.logger.error("发送咖啡制作指令失败")
            return False

    def wait_for_brewing_complete(self, timeout: int = 120) -> bool:
        """
        等待咖啡制作完成（通过持续查询状态）
        :param timeout: 超时时间（秒）
        :return: 是否成功完成制作
        """
        self.logger.info("等待咖啡制作完成...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 查询咖啡机状态
            response = self.send_command("05", "0000000D")

            if response:
                # 这里可以根据响应内容判断咖啡是否制作完成
                # 由于您要求不解析响应，我们简单假设只要有响应就继续
                self.logger.info("咖啡机状态查询成功")

                # 简单延迟后继续查询
                time.sleep(10)
            else:
                self.logger.warning("状态查询无响应")
                time.sleep(5)

        self.logger.warning("等待咖啡制作完成超时")
        return False


def main():
    # 配置串口参数
    PORT = 'COM6'  # 根据实际情况修改

    # 创建咖啡机控制器实例
    coffee_machine = CoffeeMachineController(port=PORT)

    try:
        # 连接咖啡机
        if not coffee_machine.connect():
            return

        # 发送制作美式咖啡指令
        success = coffee_machine.make_americano()
        if success:
            coffee_machine.logger.info("美式咖啡制作指令已成功发送")

            # 等待咖啡制作完成
            if coffee_machine.wait_for_brewing_complete():
                coffee_machine.logger.info("咖啡已制作完成，可以取杯")
            else:
                coffee_machine.logger.warning("咖啡制作可能未完成")
        else:
            coffee_machine.logger.error("发送美式咖啡制作指令失败")

        # 短暂延迟后断开连接
        time.sleep(5)

    except Exception as e:
        coffee_machine.logger.error(f"发生错误: {e}")
    finally:
        coffee_machine.disconnect()


if __name__ == "__main__":
    main()
# ----------------------------------------------------------------------------------------------------------------------------------------------------
