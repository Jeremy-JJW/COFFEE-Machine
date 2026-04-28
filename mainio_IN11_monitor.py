
# ------------------------------------------自己写的简化版本，加了IN8对射光电信号版本------------------------------------
import logging
import time
import threading
from  coffee_machine import CoffeeMachineController
from  yanmeng_io_reader import YanMengIOController
from order_db import OrderDatabase
# ============配置全局日志===============
logging.basicConfig(
    level = logging.INFO,
    format  = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    filename = 'Coffee_machine2.log',
    encoding='utf-8'
)
logger = logging.getLogger("Coffee Machine")

class CoffeeProductionController:

    def __init__(self,coffee_port = "COM6"):
        # 创建实例化对象
        self.io_controller = YanMengIOController()
        self.coffee_machine = CoffeeMachineController(port=coffee_port)
        self.db=OrderDatabase()  #创建order_db.py的数据库实例化对象，用以对数据库进行增删改查

        # 系统状态
        self.running = False   #咖啡制作系统（主线程）运行状态
        self.is_processing = False   #咖啡正在生产状态（制作咖啡线程正在进行中）
        self.current_order = None   #当前订单状态
        self.remaining_order = None   #剩余待处理杯数
        self.current_order_num = None   #当前订单号

        # 多线程的初始化
        # 三个线程：数据库监控、订单监控队列、生产工序
        self.db_monitor_thread = None
        self.sequence_thread = None
        self.queue_monitor_thread = None

        # 咖啡制作时间
        self.coffee_processing_time = 80    #这个咖啡制作时间还要看一下原代吗是怎么定义使用的！！！！！！！！！！！！！！！！！！！！！！！！！

        # 线程锁
        self.lock = threading.Lock()

    def start(self):
        self.running = True

        # 打开岩獴板卡/咖啡机  使用了外部类中的方法
        run_banka = self.io_controller.open_device()
        run_coffee = self.coffee_machine.connect()
        if not run_banka or not run_coffee:
            logger.error (f"板卡/咖啡机连接失败,板卡状态：{run_banka},咖啡机状态：{run_coffee}")
            print(f"板卡/咖啡机连接失败,板卡状态：{run_banka},咖啡机状态：{run_coffee}")
            return False
        # 初始化所有输出引脚状态
        for i in range(16):
            self.io_controller.write_output_pin(i,True)
        logger.info("DO信号复位完成，全部置为True")

        #创建并启动数据库监控线程
        self.db_monitor_thread = threading.Thread(
            target = self.db_monitor,
            name = "db_monitor",
            daemon = True
        )
        self.db_monitor_thread.start()

        # 创建并启动生产队列监控线程
        self.queue_monitor_thread = threading.Thread(
            target= self.queue_monitor,
            name = "queue_monitor",
            daemon = True
        )
        self.queue_monitor_thread.start()

        print("start方法执行完毕，咖啡机/板卡连接成功，所有DO信号复位完成（置为True），已启动数据库监控线程/生产队列线程")
        logger.info("start方法执行完毕，咖啡机/板卡连接成功，所有DO信号复位完成（置为True），已启动数据库监控线程/生产队列线程")
        return True

    def db_monitor(self):
        while self.running:
            try:
                #如果没有订单记录，也没有正在生产，则获取新订单    current_order  is_processing
                with self.lock:  # 加了个线程锁，确保在数据库进行读取新的数据时共享变量不会被修改
                    if not self.current_order and not self.is_processing:
                        current_order  = self.db.get_next_pending_order()   #注意这个返回回来可能是空值，所以要加一个下面的if判断
                        if current_order:
                            self.current_order_num = current_order["order_id"]
                            self.remaining_order = current_order["cups"]
                            self.current_order = current_order
                            print(f"已获得新订单，订单号为：{self.current_order_num} ， 该订单要做{self.remaining_order}杯咖啡")
                            logger.info(f"已获得新订单，订单号为：{self.current_order_num},该订单要做{self.remaining_order}杯咖啡")
                time.sleep(1)
            except Exception as e:
                logger.error(f"{e}")
                time.sleep(1)  #记得这个也要释放一下进程

    def queue_monitor(self):
        while self.running:
            try:
                with self.lock:
                    # 有当前订单 并且有剩余未处理订单 并且未在生产制作中  时，就创建并启动一个制作流程的线程
                    if self.current_order and self.remaining_order>0 and not self.is_processing:
                        logger.info("已进入queue_monitorif判断，开始创建一杯生产线程")
                        self.is_processing = True #防止再进入自己的if判断条件中
                        production_thread = threading.Thread(
                            target=self.production_sequence,
                            name="production_sequence",
                            daemon = True
                        )
                        production_thread.start()
                time.sleep(1)

            except Exception as e:
                logger.error(f"{e}")
                time.sleep(1) #记得这个也要释放一下进程

    def production_sequence(self):
        try:
            print("=====================一杯生产制作程序开始=============================")
            logger.info("=====================一杯生产制作程序开始=============================")
            # 1.触发机械臂启动  OUT1信号高——>低——>高
            self.io_controller.write_output_pin(1,False)
            time.sleep(0.5)
            self.io_controller.write_output_pin(1,True)
            print("已触发机械臂启动信号DO1")
            logger.info("已触发机械臂启动信号DO1")

            # 2.等待机械臂到位  IN11信号变化 高低高
            last_IN11 = self.io_controller.read_input_pin(11)
            while self.running:
                current_IN11 = self.io_controller.read_input_pin(11)
                if last_IN11 and not current_IN11:
                    break
            print("机械臂到位信号IN11已变化，杯子到达咖啡机口")
            logger.info("机械臂到位信号IN11已变化，杯子到达咖啡机口")


            # 3.调用制作咖啡的方式
            self.coffee_machine.make_americano()
            print("咖啡制作命令已发送")
            logger.info("咖啡制作命令已发送")

            # 4.等待咖啡制作完成
            # time.sleep(self.coffee_processing_time)
            # print("咖啡制作完成")
            # logger.info("咖啡制作完成")
            # 想到一个新的方式，不用管咖啡制作时间了，现在是等待IN8信号到位就说明咖啡做完放到了落杯器上

            # 5.等待杯子放到落杯器上  IN8信号变化
            print("等待咖啡制作完毕并放到落杯器上")
            logger.info("等待咖啡制作完毕并放到落杯器上")
            last_IN8 = self.io_controller.read_input_pin(8)
            if last_IN8:
                logger.info(f"目前IN8信号电平为{last_IN8},杯子未放到落杯器上")
                print(f"目前IN8信号电平为{last_IN8},杯子未放到落杯器上")
            time_start= time.time()
            while self.running:
                time_now = time.time()
                if time_now-time_start <100:
                    current_IN8 = self.io_controller.read_input_pin(8)
                    if last_IN8 and not current_IN8:
                        logger.info(f"杯子已落到落杯器上，3.5秒等待下降")
                        print(f"杯子已落到落杯器上，3.5秒后等待下降")
                        break
                    time.sleep(0.5)
                else:
                    return True   #当没有落下杯子，也就是超时100s还没有等到IN8信号，就直接跳出函数体，进行下一次制作
            time.sleep(3.5)

            # 6.触发落杯器下降   并再读一次IN8信号供下次判断使用，并OUT11置于低电平6s
            print("开始触发OUT11信号，让落杯器下降")
            logger.info("开始触发OUT11信号，让落杯器下降")
            self.io_controller.write_output_pin(11,False)

            last_IN8 = self.io_controller.read_input_pin(8)
            if not last_IN8:
                logger.info(f"目前IN8信号电平为{last_IN8}，杯子在落杯器上")
                print(f"目前IN8信号电平为{last_IN8}，杯子在落杯器上")

            time.sleep(6)

            self.io_controller.write_output_pin(11,True)
            print("OUT11信号已恢复为True")
            logger.info("OUT11信号已恢复为True")

            # 7.等待用户取杯 并升起起落架 就是查看IN8信号变化和控制OUT  false变为True则为取走杯子
            while self.running:
                current_IN8 = self.io_controller.read_input_pin(8)
                if  not last_IN8 and current_IN8:
                    logger.info("IN8信号已变化，初步判断用户已取走杯子")
                    print("IN8信号已变化，初步判断用户已取走杯子")
                    time.sleep(2)  #等待1.5s防止用户又放回去
                    while True:
                        if self.io_controller.read_input_pin(8): #1.5秒后再读一次IN8做一次判断，如果还为true则确定用户拿走了杯子
                            time.sleep(0.5)
                            print("第2次判断，用户确实取走了杯子")
                            logger.info("第2次判断，用户确实取走了杯子")
                            break
                        else:    #如果此时又放回去，则重新等待取杯
                            print("用户又放回去了")
                            logger.info("用户又放回去了")
                            continue
                    break

            # 升起起落架
            self.io_controller.write_output_pin(12,False)
            print("正在升起起落架")
            logger.info("正在升起起落架")
            time.sleep(6)
            self.io_controller.write_output_pin(12,True)
            print("起落架已升起，OUT12信号恢复至True")
            logger.info("起落架已升起，OUT12信号恢复至True")

            # 更新一杯咖啡完成后的状态（CSV：completed_cups +1；最后一杯再标 status=2）
            print("开始更新订单状态")
            with self.lock:
                self.remaining_order -= 1  # 剩余待做咖啡 -1
                print("已进入线程锁，开始修改订单状态")
                logger.info("已进入线程锁，开始修改订单状态")
                self.db.increment_completed_cups(self.current_order_num)
                if self.remaining_order <= 0:
                    logger.info("本次订单剩余杯数为0")
                    print("本次订单剩余杯数为0")
                    self.db.mark_order_as_completed(self.current_order_num)
                    self.current_order = None
                    self.current_order_num = None
                    print("数据库已修改，参数回到初始化，本次订单已完成")
                    logger.info("数据库已修改，参数回到初始化，本次订单已完成")
                else:
                    print(f"订单{self.current_order_num}剩余{self.remaining_order}杯待制作")
                    print("准备开始下一杯制作工序")
            return True
        except Exception as e:
                logger.error(f"{e}")
                return True
        finally:
            with self.lock:
                self.is_processing = False  #生产工序结束了，要把这个变量置回fasle，便于订单队列监控线程进入if重新生成新的生产线程

    def stop(self):
        # 停止整个系统，即将系统运行状态变量变为False
        self.running = False
        # 让生产线序线程再运行1s   join()方法
        if self.sequence_thread and self.sequence_thread.is_alive():
            self.sequence_thread.join()
            #无限期阻塞调用这个线程的方法，这里是主线程（但是数据库或者订单监控线程仍然在运行！）。
            # 然后执行sequence_thread这个线程，直到这个线程执行完毕再运行主线程
        #关闭硬件连接
        self.io_controller.close()
        self.coffee_machine.close()

        logger.info("控制器已安全停止")

if __name__ == "__main__":
    COFFEE_PORT = "COM6"

    try:
        logger.info("启动生产系统")
        # 创建实例化控制类
        controller = CoffeeProductionController(coffee_port=COFFEE_PORT)

        start = controller.start()  #让 主线程运行起来
        if start:
            try:
                while controller.running:
                    time.sleep(1)   #让主线程一直睡眠，但是还是存在。功能：1.提供用户中断机制
            except Exception as e:
                controller.stop()
    except Exception as e:
        logger.error(f"{e}")
        print("系统启动失败")


# （0）看一下这杯结束生产后的流程
# （1）把步骤log加的详细一些
# (2)是不是更新订单状态那里有问题
