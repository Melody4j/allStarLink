package com.allstarlink.dashboard.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 节点列表视图对象
 * 用于管理后台节点列表展示，包含完整的节点信息和计算字段
 *
 * @author AllStarLink Dashboard
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NodeListVO {

    /**
     * 节点ID
     */
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
     * 是否在线
     */
    private Boolean isActive;

    /**
     * 最后在线时间
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime lastSeen;

    /**
     * 节点等级：Core/Active/Transient
     */
    private String nodeRank;

    /**
     * 移动属性：Fixed/Mobile
     */
    private String mobilityType;

    /**
     * 首次入网时间
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime firstSeenAt;

    /**
     * 纬度
     */
    private Double latitude;

    /**
     * 经度
     */
    private Double longitude;

    /**
     * 是否移动节点
     */
    private Boolean isMobile;

    /**
     * 24小时活跃率(%)
     */
    private BigDecimal activityRate24h;

    /**
     * 记录更新时间
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime updateTime;
}