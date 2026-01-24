package com.allstarlink.dashboard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotNull;

/**
 * 分页查询数据传输对象
 * 用于节点列表的分页查询和条件筛选
 *
 * @author AllStarLink Dashboard
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageQueryDTO {

    /**
     * 当前页码
     */
    @NotNull(message = "页码不能为空")
    @Min(value = 1, message = "页码最小为1")
    private Long current;

    /**
     * 每页条数
     */
    @NotNull(message = "每页条数不能为空")
    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 500, message = "每页条数最大为500")
    private Long size;

    /**
     * 呼号（模糊查询）
     */
    private String callsign;

    /**
     * 所有者（模糊查询）
     */
    private String owner;

    /**
     * 组织名称（模糊查询）
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
     * 节点等级：Core/Active/Transient
     */
    private String nodeRank;

    /**
     * 移动属性：Fixed/Mobile
     */
    private String mobilityType;

    /**
     * 是否移动节点
     */
    private Boolean isMobile;

    /**
     * 排序字段：nodeId/callsign/country/lastSeen/firstSeenAt/updateTime
     */
    private String sortField = "updateTime";

    /**
     * 排序方向：asc/desc
     */
    private String sortOrder = "desc";

    /**
     * 获取排序的起始位置
     * @return 起始位置
     */
    public Long getOffset() {
        return (current - 1) * size;
    }

    /**
     * 验证排序参数
     * @return 是否有效
     */
    public boolean isValidSort() {
        return sortField != null && (sortOrder.equals("asc") || sortOrder.equals("desc"));
    }
}