package com.allstarlink.dashboard.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.*;

import java.time.LocalDateTime;

/**
 * 节点维度表实体类
 * 对应数据库表：dim_nodes
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
@TableName("dim_nodes")
public class DimNodes {

    /**
     * 节点ID，主键
     */
    @TableId(value = "node_id", type = IdType.INPUT)
    private Integer nodeId;

    /**
     * 呼号
     */
    private String callsign;

    /**
     * 所有者
     */
    private String owner;

    /**
     * 组织名称
     */
    private String affiliation;

    /**
     * 组织类型：Personal/Club/System
     */
    @TableField("affiliation_type")
    private String affiliationType;

    /**
     * 国家
     */
    private String country;

    /**
     * 大洲
     */
    private String continent;

    /**
     * 当前是否在线
     */
    @TableField("is_active")
    private Boolean isActive;

    /**
     * 最后一次在线时间
     */
    @TableField("last_seen")
    private LocalDateTime lastSeen;

    /**
     * 节点等级：Core/Active/Transient
     */
    @TableField("node_rank")
    private String nodeRank;

    /**
     * 移动属性：Fixed(固定)/Mobile(移动)
     */
    @TableField("mobility_type")
    private String mobilityType;

    /**
     * 节点首次入网时间
     */
    @TableField("first_seen_at")
    private LocalDateTime firstSeenAt;

    /**
     * 本记录最后更新时间
     */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 最新纬度
     */
    private Double latitude;

    /**
     * 最新经度
     */
    private Double longitude;

    /**
     * 是否为移动节点（根据DWD位移历史判定）
     */
    @TableField("is_mobile")
    private Boolean isMobile;
}