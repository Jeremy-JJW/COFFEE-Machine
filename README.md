# COFFEE-Machine
联动JAKA协作机械臂、咖啡机、板卡、工控机、电气元器件等设备，实现扫码点单到cobot取杯+取咖啡液+落杯的完整流程，实现自助咖啡零售机功能。

文件说明：

1.app.py是一个flask框架搭建出的咖啡点单页面；

2.coffee_machine.py是咖啡机控制SDK，封装了很多咖啡机操作方法；

3.mainio_IN11_monitor.py是制作总控程序；

4.laubcher2.py是一个快捷启动的程序，用于不会python程序的人员运行项目；

5.order_db.py是数据库控制程序，封装了很多对数据库操作的方法（这里的数据库就是CSV文件）；

6.start_work.py是一个完全断电后重启咖啡机和JAKA机器人（上使能+运行程序）的程序，运行即可自动重启；

7.yanmeng_io_reader.py封装了岩獴RM1616板卡的操作方法。
