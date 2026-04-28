# power_on_devices.py - 独立设备开机程序
import time
import logging
from yanmeng_io_reader import YanMengIOController

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PowerOnSequence")


def power_on_devices():
    """独立设备开机程序 - 启动咖啡机和机械臂"""
    # 显示开机说明
    print("=" * 68)
    print("            设备开机程序 - 独立执行")
    print("=" * 68)
    print("说明:")
    print("1. 本程序仅用于设备完全断电后重新启动")
    print("2. 程序将发送3秒开机信号到以下设备:")
    print("   - 我OUT0 -> JAKA机械臂")
    print("   - 我OUT7 -> 咖啡机")
    print("3. 信号时序: 高电平(true) => 低电平(false) [持续3秒] => 高电平(true)")
    print("4. 程序退出后将不会再次发送开机信号")
    print("=" * 68)
    print("警告: 只有设备完全断电后才需要执行此程序")
    print("=" * 68)

    # 确认是否继续
    confirm = input("是否继续执行开机程序? [y/n]: ").lower()
    if confirm != 'y':
        logger.info("用户取消开机程序")
        return

    # 创建IO控制器
    io_controller = YanMengIOController()

    # 设备开机相关引脚定义
    ARM_START_PIN = 0  # OUT0 -> JAKA机械臂
    COFFEE_PIN = 7  # OUT7 -> 咖啡机

    # 设备开机逻辑
    try:
        # 打开设备连接
        if not io_controller.open_device():
            logger.error("无法打开岩獴板卡")
            logger.error("可能原因: ")
            logger.error("1. 岩獴板卡未连接")
            logger.error("2. 无访问权限或DLL不存在")
            logger.error("3. 板卡已被其他程序占用")
            logger.error("4. 设备驱动程序未安装")
            return False

        logger.info("✅ 岩獴板卡连接成功")

        # 初始状态 - 全部高电平(true)
        logger.info("初始化设备信号状态...")
        io_controller.write_output_pin(ARM_START_PIN, True)
        io_controller.write_output_pin(COFFEE_PIN, True)
        logger.info("✅ 所有开机信号初始化为高电平(true)")

        # 执行开机程序
        logger.info("🟢 开始执行开机程序...")

        # 发送开机信号 - 低电平(false)
        logger.info("发送机械臂开机信号(OUT0): 高电平(true) → 低电平(false)")
        io_controller.write_output_pin(ARM_START_PIN, False)

        logger.info("发送咖啡机开机信号(OUT7): 高电平(true) → 低电平(false)")
        io_controller.write_output_pin(COFFEE_PIN, False)

        # 保持低电平3秒
        logger.info("保持开机信号3秒(预防继电器延迟)...")
        for i in range(3, 0, -1):
            logger.info(f"倒计时: {i}秒")
            time.sleep(1)

        # 恢复初始状态
        logger.info("恢复初始状态...")
        logger.info("恢复机械臂开机信号(OUT0): 低电平(false) → 高电平(true)")
        io_controller.write_output_pin(ARM_START_PIN, True)

        logger.info("恢复咖啡机开机信号(OUT7): 低电平(false) → 高电平(true)")
        io_controller.write_output_pin(COFFEE_PIN, True)

        logger.info("✅ 开机程序执行完成")
        logger.info("请在设备面板确认机械臂和咖啡机是否已成功启动")

        # # 询问是否验证状态
        # if input("是否验证开机信号状态? [y/n]: ").lower() == 'y':
        #     arm_state = io_controller.read_output_pin(ARM_START_PIN)
        #     coffee_state = io_controller.read_output_pin(COFFEE_PIN)
        #
        #     arm_ok = arm_state is True
        #     coffee_ok = coffee_state is True
        #
        #     logger.info(f"机械臂开机信号状态: {'高电平(✅)' if arm_ok else '低电平(❌)'}")
        #     logger.info(f"咖啡机开机信号状态: {'高电平(✅)' if coffee_ok else '低电平(❌)'}")
        #
        #     if not (arm_ok and coffee_ok):
        #         logger.warning("⚠️ 信号状态未恢复! 请手动检查设备连接")

        # 安全关闭设备
        logger.info("关闭板卡连接...")
        io_controller.close_device()
        logger.info("✅ 设备安全断开")
        logger.info("开机程序已完成")

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断开机程序! 正在恢复信号...")
        try:
            io_controller.write_output_pin(ARM_START_PIN, True)
            io_controller.write_output_pin(COFFEE_PIN, True)
            logger.info("信号已恢复为高电平")
        except:
            logger.error("恢复信号失败!")
        return False

    except Exception as e:
        logger.error(f"开机程序执行失败: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    # 启动开机程序
    power_on_devices()
