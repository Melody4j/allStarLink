📊 AllStarLink dim_nodes 表结构变更说明 (V2.0)
1. 字段重命名与标准化 (Standardization)
为了降低爬虫代码的字段映射成本，将部分自定义命名调整为 API 原生命名：
原字段名	新字段名	变更说明
site	site_name	增强语义，明确为物理站点名称。
can_telephone	access_telephoneportal	对齐 API，标识是否开启电话网关。
can_web_tx	access_webtransceiver	对齐 API，标识是否支持网页对讲。
has_function_list	access_functionlist	对齐 API，标识是否开放远程功能列表查询。
2. 存量字段含义修正 (Session Stats)
明确了统计频率，将原本模糊的累计字段定义为 “单次开机会话” 数据：
total_keyups: 注释变更为 本次在线累积ptt次数。
total_tx_time: 注释变更为 本次在线累积发射时长。
3. 新增高价值画像字段 (New Analytics Fields)
新增字段主要用于历史资产累加、故障监测及协议识别：
历史资产类：
history_total_keyups: 节点自发现以来的总 PTT 次数。
history_tx_time: 节点自发现以来的总发射时长。
运行质量类：
seqno: 上报序号。用于监测数据新鲜度。
timeout: 发射限时中断次数。用于判定设备故障或“长话王”。
apprptuptime: 本次在线时长（秒）。判定节点稳定性的核心指标。
totalexecdcommands: 本次执行命令数。判定管理员活跃度的指标。
功能控制类：
access_reverseautopatch: 是否允许从电话端反向拨入无线电。
节点属性类：



以下是最新的dim_nodes表结构：
-- allStarLink.dim_nodes definition

CREATE TABLE `dim_nodes` (
  `node_id` int(11) NOT NULL COMMENT '节点ID，主键',
  `node_type` varchar(20) NOT NULL COMMENT '节点所属系统类型：ALLSTARLINK/ECHOLINK/IRLP/WIRESX',
  `callsign` varchar(20) DEFAULT NULL,
  `frequency` varchar(50) DEFAULT NULL COMMENT '最新工作频率',
  `tone` varchar(20) DEFAULT NULL COMMENT '最新亚音',
  `owner` varchar(100) DEFAULT NULL,
  `affiliation` varchar(100) DEFAULT NULL,
  `site_name` varchar(100) DEFAULT NULL COMMENT '最新物理站点名称',
  `features` varchar(100) DEFAULT NULL COMMENT '最新功能标签(废弃)',
  `affiliation_type` varchar(20) DEFAULT NULL COMMENT '组织类型：Personal/Club/System',
  `country` varchar(100) DEFAULT NULL,
  `continent` varchar(50) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL COMMENT '当前是否在线',
  `last_seen` datetime DEFAULT NULL COMMENT '最后一次在线时间',
  `node_rank` varchar(20) DEFAULT NULL COMMENT '节点等级：Core/Active/Transient',
  `mobility_type` varchar(20) DEFAULT NULL COMMENT '移动属性：Fixed(固定)/Mobile(移动)',
  `first_seen_at` datetime DEFAULT NULL COMMENT '节点首次入网时间',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '记录首次创建时间',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '本记录最后更新时间',
  `latitude` double DEFAULT NULL COMMENT '最新纬度',
  `longitude` double DEFAULT NULL COMMENT '最新经纬',
  `location_desc` varchar(200) DEFAULT NULL COMMENT '原始位置描述文本',
  `is_mobile` tinyint(1) DEFAULT '0' COMMENT '是否为移动节点（根据DWD位移历史判定）',
  `app_version` varchar(20) DEFAULT NULL COMMENT 'ASL软件版本',
  `is_bridge` tinyint(1) DEFAULT '0' COMMENT '是否为数字网关/桥接器',
  `access_webtransceiver` tinyint(1) DEFAULT '0' COMMENT '是否支持网页收发',
  `ip_address` varchar(45) DEFAULT NULL COMMENT '最后报告的IP地址',
  `timezone_offset` decimal(3,1) DEFAULT NULL COMMENT '时区偏移量',
  `is_nnx` tinyint(1) DEFAULT '0' COMMENT '是否使用NNX协议',
  `hardware_type` varchar(50) DEFAULT NULL COMMENT '硬件类型预测(根据OS/版本猜测)',
  `total_keyups` bigint(20) DEFAULT '0' COMMENT '本次在线累积ptt次数',
  `history_total_keyups` bigint(20) DEFAULT '0' COMMENT '历史累积ptt次数',
  `total_tx_time` bigint(20) DEFAULT '0' COMMENT '本次在线累积发射时长',
  `history_tx_time` bigint(20) DEFAULT '0' COMMENT '历史累积发射时长',
  `avg_talk_length` decimal(10,2) DEFAULT '0.00' COMMENT '平均单次通话时长',
  `access_telephoneportal` tinyint(1) DEFAULT '0' COMMENT '是否支持电话网关接入',
  `access_functionlist` tinyint(1) DEFAULT '0' COMMENT '是否支持远程功能列表查询',
  `access_reverseautopatch` tinyint(1) DEFAULT '0' COMMENT '是否允许反向自动拨号',
  `seqno` bigint(20) DEFAULT '0' COMMENT '上报序号',
  `timeout` int(11) DEFAULT '0' COMMENT '发射限时中断次数',
  `apprptuptime` bigint(20) DEFAULT '0' COMMENT '本次在线时长',
  `totalexecdcommands` int(11) DEFAULT '0' COMMENT '本次在线执行命令行次数',
  `max_uptime` bigint(20) DEFAULT '0' COMMENT '历史最大连续在线时长(秒)',
  `current_link_count` int(11) DEFAULT '0' COMMENT '当前实时连接数',
  PRIMARY KEY (`node_id`,`node_type`),
  KEY `idx_geo` (`latitude`,`longitude`),
  KEY `idx_app_version` (`app_version`),
  KEY `idx_is_bridge` (`is_bridge`),
  KEY `idx_keyups` (`total_keyups`),
  KEY `idx_link_count` (`current_link_count`),
  KEY `idx_node_type` (`node_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;