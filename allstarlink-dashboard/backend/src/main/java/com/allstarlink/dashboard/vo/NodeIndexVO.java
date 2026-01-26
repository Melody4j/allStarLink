
package com.allstarlink.dashboard.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 节点索引VO
 * 用于全量节点缓存，仅包含必要的轻量级字段
 *
 * @author AllStarLink Dashboard
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NodeIndexVO {

    /**
     * 节点ID
     */
    private Integer nodeId;

    /**
     * 呼号
     */
    private String callsign;

    /**
     * 纬度
     */
    private Double latitude;

    /**
     * 经度
     */
    private Double longitude;

    /**
     * 是否在线
     */
    private Boolean isActive;

    /**
     * 节点等级：Core/Active/Transient
     */
    private String nodeRank;

    /**
     * 组织类型：Personal/Club/System
     */
    private String affiliationType;

    /**
     * 国家
     */
    private String country;
}
