# 考勤系统

- [使用说明](#使用说明)
- [功能](#功能)
- [需求](#需求)
- [开发进度](#开发进度)
- [待完成](#待完成)

## 使用说明

- 环境：

  - centos 6.3 64位 / Windows10 64位（没有验证 Windows10 的 Nginx）
  - python3.6  64位
  - Nginx + uWSGI
  - Django 1.11版本 （其他版本没有验证）
  - [django-bootstrap3](https://github.com/dyve/django-bootstrap3)
  - [xlrd](https://github.com/python-excel/xlrd)
  - [xadmin](https://github.com/sshwsfc/xadmin) (这个需要下载到本地，用 pip3.6 install xadmin )

- 环境准备

  - [阿里云ECS centos7.3 下安装 python3.6 ](https://blog.csdn.net/wengzilai/article/details/78621407)
  - ```pip3.6 install Django=1.11```
  - ```yum install git```
  - 克隆这个库到本地   ```git clone https://github.com/fhrl94/Attendance.git```（本文档路径默认为`/root/Attendance` ）
  - ``` pip3.6 install xlrd```
  - ```pip3.6 install django-bootstrap3```
  - 下载 [xadmin](https://github.com/sshwsfc/xadmin)  用 ```pip install``` 安装  (这个需要下载到本地，用 pip3.6 install xadmin )

- 初始化 Django
  - 进入 `Attendance/` 路径，运行
    ```
    python3.6 manage.py makemigrations
    python3.6 manege.py migrate
    python3.6 manage.py createsuperuser
    # 此处需要输入管理员邮箱、账号、密码
    python3.6 manage.py collectstatic
    python3.6 manage.py runserver 0.0.0.0:8000
    ```
  - 进入[管理员界面](localhost:8000/xadmin) localhost:8000/xadmin

- 数据导入注意事项，**导入的文件均为 XLS 格式， XLS读取** ，有需要的可以自行调整

  - 【员工基本信息】 &rArr; 【导入】，导入模板为：

    | user ptr | id   | password | last_login | is_superuser | groups | user_permissions | username | first_name | last_name | email | is_staff | is_active | date_joined           | code | name | level | emp_status | pwd_status |
    | -------- | ---- | -------- | ---------- | ------------ | ------ | ---------------- | -------- | ---------- | --------- | ----- | -------- | --------- | --------------------- | ---- | ---- | ----- | ---------- | ---------- |
    | 登录账号     | 2    |          |            | FALSE        |        |                  | 登录账号     |            |           |       | FALSE    | TRUE      | 2018-06-04   10:30:00 | 工号   | 姓名   | 级别    | 在职         | FALSE      |

    - 密码设置为，user 表中 hash 之后的密码，可以自行设置密码后，获取 hash 值

    - 工号长度必须为 10 ，[修改文件链接](https://github.com/fhrl94/Attendance/blob/master/Attendance/models.py#L28)  修改完成后需要执行

      ```
      python3.6 manage.py makemigrations
      python3.6 manege.py migrate
      ```

  - 【考勤数据导入】 &rArr; 【新增记录】时，添加的文件表头中必须要包含：**`工号、出勤时间`**

    - 出勤时间的格式为 `yyyy-mm-dd hh:mm:ss`

  - 【班次信息】,案例如下：

    | 班次名称                | 是否工作日 | 上午上班时间 | 上午打卡截止时间 | 下午下班开始时间 | 下午下班时间 | 迟到起始值（分） | 早退起始值（分） | 旷工起始值（分） | 班次状态 |
    | ------------------- | ----- | ------ | -------- | -------- | ------ | -------- | -------- | -------- | ---- |
    | 主管/经理-哺乳假下午         | 是     | 08:15  | 12:30    | 13:30    | 18:15  | 0        | 60       | 120      | 使用中  |
    | 主管/经理-哺乳假上午         | 是     | 08:15  | 12:30    | 13:30    | 18:15  | 60       | 0        | 120      | 使用中  |
    | 高管班次（8:15-18:30）    | 是     | 08:15  | 12:30    | 13:30    | 18:30  | 0        | 0        | 120      | 使用中  |
    | 主管/经理班次（8:15-18:15） | 是     | 08:15  | 12:30    | 13:30    | 18:15  | 0        | 0        | 120      | 使用中  |
    | 员工班次（8:30-18:00）    | 是     | 08:30  | 12:30    | 13:30    | 18:00  | 0        | 0        | 120      | 使用中  |
    | 节假日班次               | 否     | 08:30  | 12:30    | 13:30    | 18:00  | 0        | 0        | 120      | 使用中  |

  - 【法定节假日】添加当月/全年的节假日

  - 【考证状态类型】 &rArr; 【增加 考勤状态类型】：

    - **必须要添加以下2个**

    | 考勤异常状态名称 | 异常编码 | 使用状态 |
    | ---------------- | -------- | -------- |
    | 打卡             | DK00     | 使用中   |
    | 未打卡           | DK01     | 使用中   |



  - 【签卡类型】 &rArr; 【导入】；**XLS模板**如下，按各自需求更改：

    | attendanceexceptionstatus  ptr | id   | exception_name | exception_code | exception_status | exception_operate   |
    | ------------------------------ | ---- | -------------- | -------------- | ---------------- | ------------------- |
    | 其他                             | 10   | 其他             | Qk09           | 1                | 2018-06-12 11:00:56 |
    | 出差（签卡）                         | 9    | 出差（签卡）         | QK08           | 1                | 2018-06-12 11:00:56 |
    | 特批                             | 8    | 特批             | Qk07           | 1                | 2018-06-12 11:00:56 |
    | 班车迟到                           | 7    | 班车迟到           | QK06           | 1                | 2018-06-12 11:00:56 |
    | 查监控已打卡                         | 6    | 查监控已打卡         | QK05           | 1                | 2018-06-12 11:00:56 |
    | 查监控忘打卡                         | 5    | 查监控忘打卡         | QK04           | 1                | 2018-06-12 11:00:56 |
    | 因公外出                           | 4    | 因公外出           | QK03           | 1                | 2018-06-12 11:00:56 |
    | 参会                             | 3    | 参会             | QK02           | 1                | 2018-06-12 11:00:56 |
    | 见客户                            | 2    | 见客户            | QK01           | 1                | 2018-06-12 11:00:56 |

  - 【请假类型】 &rArr; 【导入】；**XLS模板**如下，按各自需求更改：

    | attendanceexceptionstatus  ptr | id   | exception_name | exception_code | exception_status | exception_operate   | leave_type | legal_include |
    | ------------------------------ | ---- | -------------- | -------------- | ---------------- | ------------------- | ---------- | ------------- |
    | 事假                             | 11   | 事假             | QJ01           | 1                | 2018-06-12 11:03:25 | FALSE      | FALSE         |
    | 病假                             | 12   | 病假             | QJ02           | 1                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 年假                             | 13   | 年假             | QJ03           | 1                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 婚假                             | 14   | 婚假             | QJ04           | 1                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 丧假                             | 15   | 丧假             | QJ05           | 1                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 产假                             | 16   | 产假             | QJ06           | 1                | 2018-06-12 11:03:25 | FALSE      | TRUE          |
    | 陪产假                            | 17   | 陪产假            | QJ07           | 1                | 2018-06-12 11:03:25 | FALSE      | TRUE          |
    | 出差（请假）                         | 18   | 出差（请假）         | QJ08           | 1                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 其他假                            | 19   | 其他假            | QJ09           | 0                | 2018-06-12 11:03:25 | FALSE      | FALSE         |
    | 工伤假                            | 20   | 工伤假            | QJ10           | 0                | 2018-06-12 11:03:25 | TRUE       | FALSE         |
    | 探亲假                            | 21   | 探亲假            | QJ11           | 0                | 2018-06-12 11:03:25 | TRUE       | FALSE         |

- 上述工作准备完成后，进行数据处理

  - 在【员工基本信息】中选择人员，点击右下角【选择了 XXX 个】下拉，选择【排班选择 员工基本信息】完成排班
  - 若需要进行调班，则在【员工基本信息】中选择人员，点击右下角【选择了 XXX 个】下拉，选择【调班 员工基本信息】完成排班
  - 完成排班后，在【员工基本信息】中选择人员，点击右下角【选择了 XXX 个】下拉，选择【考勤计算 员工基本信息】/【考勤汇总 员工基本信息】进行计算、汇总。

- 在【考勤明细查看】/【考勤信息汇总】中查看考勤信息

- Nginx 部署

  - 路径默认为`/root/Attendance` ， 如有调整，请修改[Attendance_nginx.conf](https://github.com/fhrl94/Attendance/blob/master/Attendance_nginx.conf) 、[Attendance_uwsgi.ini](https://github.com/fhrl94/Attendance/blob/master/Attendance_uwsgi.ini) 文件中的路径

  - 安装 uWSGI

    `pip3.6 install uWSGI`

  - 安装 Nginx

    `yum install epel-release`

    `yum install python-devel nginx`

    ```
    ln -s /root/Attendance/Attendance_nginx.conf /etc/nginx/conf.d/Attendance_nginx.conf
    # 需要修改 /root/Attendance/Attendance_nginx.conf 中
    # server_name  服务器的外网IP或域名;
    ```

  - 启动 Nginx

    ` /bin/systemctl restart nginx.service `

  - 启动 Django （此时需要关闭运行 `python3.6 manage.py runserver 0.0.0.0:8000` 的窗口）

    `uwsgi --ini /root/Attendance/Attendance_uwsgi.ini`

    **遇到问题，可以查看[Attendance_nginx.conf](https://github.com/fhrl94/Attendance/blob/master/Attendance_nginx.conf) 、[Attendance_uwsgi.ini](https://github.com/fhrl94/Attendance/blob/master/Attendance_uwsgi.ini) 文件中的备注**

- 培训思维导图

  **考勤系统**
  ```
  考勤专员
  	每日
  		考勤数据导入
  		点击考勤计算
  		每日异常查看
  	每月
  		法定节假日新增
  		月初人员排班
  			排班
  			调班
  	日常维护
  		新员工入职
  			基本信息录入
  			人员排班
  			当天上午打卡记录导入
  			登录网址传递？
  		员工离职/离职未办
  			排班删除
          请假/签卡信息维护
  	其他
  		班次新增/禁用
  		签卡类型新增/禁用
  		请假类型新增/禁用
  员工
  	考勤明细
  	考勤汇总
  	签卡明细
  	请假明细
  	年假额度
  		待开发
  	常见问题说明
  ```

## 待完成

- 假期额度模块

## 开发进度

- 2018.6.15 请假/签卡维护界面，重复单据时，友好界面提示；每次解析考勤原始文件，会存储相同数据bug修复；描叙性词语修改
- 2018.6.8 班次维护后实时更新、员工查询数据时考勤自动重算范围限定（本月到上月）、界面优化
- 2018.6.1 用户界面完成
- 2018.5.25 测试数据，并修改bug
- 2018.5.18 考勤汇总模块完成
- 2018.5.10 考勤明细模块完成
- 2018.5.4 请假模块完成
- 2018.4.28 签卡模块完成
- 2018.4.19 考勤计算
- 2018.4.18 实现人员调班
- 2018.4.17 实现人员排班
- 2018.4.4 找到嵌入点，通过 action 取得模板填充的数据（看起来没有脱离后台页面）
- 2018.3.29 尝试使用[xadmin](https://github.com/sshwsfc/xadmin)
- 2018.3.28 人员数据导入、考勤数据导入(实际完成时间 3-29）
- 2018.3.27 完成初步的表格设计

## 需求

1. 考勤原始数据    导入存储（上传文件）

2. 班次、排班规则

3. 考勤排班（时间、班次、人员） 调班（时间、人员）

4. 签卡(签卡类型）

5. 请假（请假单、请假拆分、请假类型）

6. 考勤计算（人员、日期）

7. 所有员工能登录系统并查看考勤及异常

8. 考勤报表自动生成

9. 人员信息维护


## 功能

1. 考勤专员管理界面
    - 人员信息
        - 人员基础信息
        - 考勤打卡信息
        - 考勤排班信息
    - 考勤处理（考勤汇总导出）
        - 请假处理
        - 签卡签卡
    - 初始配置
        - 班次信息维护
        - 法定节假日
2. 员工查看界面
    - 考勤数据查看
    - 假期额度查询
3. 管理员配置
    - 初始班次信息
    - 签卡原因
    - 请假类型
    - 考勤状态

