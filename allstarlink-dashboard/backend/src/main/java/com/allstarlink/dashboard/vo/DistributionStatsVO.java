package com.allstarlink.dashboard.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 分布统计视图对象
 * 用于全球节点分布统计（饼图数据），支持按大洲或国家维度统计
 *
 * @author AllStarLink Dashboard
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DistributionStatsVO {

    /**
     * 统计维度名称
     */
    private String dimensionName;

    /**
     * 总节点数
     */
    private Integer totalCount;

    /**
     * 活跃节点数
     */
    private Integer activeCount;

    /**
     * 活跃率
     */
    private BigDecimal activeRate;

    /**
     * 占总体比例
     */
    private BigDecimal percentage;
}