package com.allstarlink.dashboard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.DecimalMax;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotNull;

/**
 * 地图区域查询数据传输对象
 * 用于地图可视区域按需加载的查询参数
 *
 * @author AllStarLink Dashboard
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MapBoundsQueryDTO {

    /**
     * 最小经度
     */
    @NotNull(message = "最小经度不能为空")
    @DecimalMin(value = "-180.0", message = "经度范围必须在-180.0到180.0之间")
    @DecimalMax(value = "180.0", message = "经度范围必须在-180.0到180.0之间")
    private Double minLng;

    /**
     * 最大经度
     */
    @NotNull(message = "最大经度不能为空")
    @DecimalMin(value = "-180.0", message = "经度范围必须在-180.0到180.0之间")
    @DecimalMax(value = "180.0", message = "经度范围必须在-180.0到180.0之间")
    private Double maxLng;

    /**
     * 最小纬度
     */
    @NotNull(message = "最小纬度不能为空")
    @DecimalMin(value = "-90.0", message = "纬度范围必须在-90.0到90.0之间")
    @DecimalMax(value = "90.0", message = "纬度范围必须在-90.0到90.0之间")
    private Double minLat;

    /**
     * 最大纬度
     */
    @NotNull(message = "最大纬度不能为空")
    @DecimalMin(value = "-90.0", message = "纬度范围必须在-90.0到90.0之间")
    @DecimalMax(value = "90.0", message = "纬度范围必须在-90.0到90.0之间")
    private Double maxLat;

    /**
     * 缩放级别
     */
    @NotNull(message = "缩放级别不能为空")
    @Min(value = 1, message = "缩放级别最小为1")
    @Max(value = 18, message = "缩放级别最大为18")
    private Integer zoomLevel;

    /**
     * 验证坐标边界的合理性
     * @return 是否有效
     */
    public boolean isValidBounds() {
        return minLng != null && maxLng != null && minLat != null && maxLat != null
                && minLng < maxLng && minLat < maxLat;
    }

    /**
     * 计算区域面积（粗略估算）
     * @return 区域面积
     */
    public Double calculateArea() {
        if (!isValidBounds()) {
            return 0.0;
        }
        return (maxLng - minLng) * (maxLat - minLat);
    }
}